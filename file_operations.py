"""Journaled filesystem operations; recovery uses recorded file identities.

The complete move graph is persisted before touching source files. Temporary
and recovery paths are predetermined so recovery also works after process exit.
"""
from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from contextlib import contextmanager
from functools import wraps
from pathlib import Path


class OperationCancelled(Exception):
    """Raised when the user requests a safe copy cancellation."""


def _storage():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'AnimeRenamer'


def _paths():
    directory = _storage()
    directory.mkdir(parents=True, exist_ok=True)
    return directory / 'pending_v2.json', directory / 'rename_history_v2.json'


@contextmanager
def _operation_lock():
    pending, _ = _paths()
    with (pending.parent / 'operation.lock').open('a+b') as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def _exclusive(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            with _operation_lock():
                return function(*args, **kwargs)
        except OSError as exc:
            return {'ok': False, 'message': f'另一个窗口正在操作，或记录目录不可用：{exc}', 'count': 0}
    return wrapped


def fingerprint(path):
    s = Path(path).stat()
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns]


def _matches(path, expected, identity_only=False):
    try:
        actual = fingerprint(path)
        return actual[:2] == expected[:2] if identity_only else actual == list(expected)
    except OSError:
        return False


def _write_json(path, data):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _reserve_journal(path, data):
    # Exclusive creation serializes application instances without stale lockfiles.
    with path.open('x', encoding='utf-8') as stream:
        try:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        except Exception:
            stream.close()
            path.unlink(missing_ok=True)
            raise


def _move(src, dst):
    """Never overwrite a newly arrived unrelated file."""
    src, dst = Path(src), Path(dst)
    if dst.exists():
        raise FileExistsError(f'目标已存在：{dst}')
    if os.name == 'nt':
        os.rename(src, dst)  # Windows rename fails if destination exists.
    else:
        os.link(src, dst)
        try:
            src.unlink()
        except OSError:
            dst.unlink()
            raise


def pending_operation():
    return _paths()[0].exists()


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _recover_moves(journal):
    found = []
    for rec in journal['items']:
        locations = list(dict.fromkeys(rec[k] for k in ('src', 'tmp', 'dst', 'recovery')))
        candidates = [Path(p) for p in locations if _matches(p, rec['signature'])]
        if len(candidates) != 1:
            raise RuntimeError(f'无法唯一确认原文件的位置或文件已改变：{rec["src"]}')
        found.append((rec, candidates[0]))
    # All files must vacate the graph before ANY original name is restored.
    for rec, current in found:
        recovery = Path(rec['recovery'])
        if current != recovery:
            _move(current, recovery)
    for rec, _ in found:
        _move(rec['recovery'], rec['src'])


def _remove_copies(journal):
    candidates = []
    for rec in journal['items']:
        for key in ('tmp', 'dst'):
            path = Path(rec[key])
            if not path.exists():
                continue
            signature = rec.get('copy_signature') if key == 'dst' else rec.get('copy_identity')
            if not signature or not _matches(path, signature, identity_only=key == 'tmp'):
                raise RuntimeError(f'复制文件已改变或无法确认归属，未删除：{path}')
            candidates.append(path)
    for path in candidates:
        path.unlink()


def _is_committed(journal, history):
    if not history.exists():
        return False
    data = _read(history)
    field = 'undo_id' if journal['action'] == 'undo' else 'operation_id'
    return data.get(field) == journal['operation_id']


@_exclusive
def recover_pending():
    try:
        pending, history = _paths()
        if not pending.exists():
            return {'ok': True, 'message': '没有未完成的操作。', 'count': 0}
        journal = _read(pending)
        if not _is_committed(journal, history):
            if journal['mode'] == 'rename':
                _recover_moves(journal)
            else:
                _remove_copies(journal)
                if journal['action'] == 'undo':
                    _write_json(history, {'undo_id': journal['operation_id'], 'items': []})
        pending.unlink()
        return {'ok': True, 'message': '已恢复未完成的操作。', 'count': len(journal['items'])}
    except Exception as exc:
        return {'ok': False, 'message': f'恢复尚未完成，记录已保留，请排除占用后重试：{exc}', 'count': 0}


def _make_journal(pairs, mode, action='execute'):
    records = []
    for src, dst in pairs:
        src, dst = Path(src).resolve(), Path(dst).resolve()
        token = uuid.uuid4().hex
        temp_parent = src.parent if mode == 'rename' else dst.parent
        records.append({'src': str(src), 'dst': str(dst),
                        'tmp': str(temp_parent / f'.__anime_renamer_{token}{src.suffix}'),
                        'recovery': str(src.parent / f'.__anime_recovery_{token}{src.suffix}'),
                        'signature': fingerprint(src)})
    return {'version': 2, 'operation_id': uuid.uuid4().hex, 'mode': mode,
            'action': action, 'items': records}


def _copy_record(rec, pending, journal, *, progress=None, cancel_event=None,
                 item_index=0, item_count=1, completed_bytes=0, total_bytes=0, started_at=None):
    src, temp = Path(rec['src']), Path(rec['tmp'])
    temp.parent.mkdir(parents=True, exist_ok=True)
    file_size = int(rec['signature'][2])
    copied_file = 0
    last_report = 0.0
    started_at = started_at or time.monotonic()

    def cancelled():
        return bool(cancel_event is not None and cancel_event.is_set())

    def report(force=False):
        nonlocal last_report
        if not progress:
            return
        now = time.monotonic()
        if not force and now - last_report < 0.10:
            return
        total_copied = completed_bytes + copied_file
        elapsed = max(now - started_at, 0.001)
        speed = total_copied / elapsed
        progress(item_index + 1, item_count, src.name, total_copied, total_bytes,
                 copied_file, file_size, speed)
        last_report = now

    class CopyReader:
        def __init__(self, stream):
            self.stream = stream

        def read(self, length=-1):
            if cancelled():
                raise OperationCancelled('用户取消复制')
            return self.stream.read(length)

    class CopyWriter:
        def __init__(self, stream):
            self.stream = stream

        def write(self, data):
            nonlocal copied_file
            if cancelled():
                raise OperationCancelled('用户取消复制')
            written = self.stream.write(data)
            copied_file += written
            report(force=copied_file >= file_size)
            return written

    if cancelled():
        raise OperationCancelled('用户取消复制')
    with temp.open('xb') as output:
        rec['copy_identity'] = fingerprint(temp)
        _write_json(pending, journal)
        with src.open('rb') as source:
            shutil.copyfileobj(CopyReader(source), CopyWriter(output), length=1024 * 1024)
        if file_size == 0:
            report(force=True)
        output.flush()
        os.fsync(output.fileno())
    if cancelled():
        raise OperationCancelled('用户取消复制')
    if not _matches(src, rec['signature']):
        raise RuntimeError(f'复制期间原文件改变：{src}')
    shutil.copystat(src, temp)
    rec['copy_signature'] = fingerprint(temp)
    _write_json(pending, journal)
    return copied_file


def _run(journal, progress=None, cancel_event=None):
    pending, history = _paths()
    # Nothing may touch media if journal creation or flushing fails.
    _reserve_journal(pending, journal)
    try:
        items = journal['items']
        total_bytes = sum(int(rec['signature'][2]) for rec in items) if journal['mode'] == 'copy' else 0
        completed_bytes = 0
        started_at = time.monotonic()
        for index, rec in enumerate(items):
            if not _matches(rec['src'], rec['signature']):
                raise RuntimeError(f'文件已改变，请重新预览：{rec["src"]}')
            if journal['mode'] == 'rename':
                _move(rec['src'], rec['tmp'])
                if progress:
                    progress(index + 1, len(items), Path(rec['src']).name)
            else:
                copied = _copy_record(
                    rec, pending, journal, progress=progress, cancel_event=cancel_event,
                    item_index=index, item_count=len(items), completed_bytes=completed_bytes,
                    total_bytes=total_bytes, started_at=started_at)
                completed_bytes += copied
        for rec in items:
            if journal['mode'] == 'copy' and cancel_event is not None and cancel_event.is_set():
                raise OperationCancelled('用户取消复制')
            _move(rec['tmp'], rec['dst'])
        if journal['mode'] == 'copy' and cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled('用户取消复制')
        if journal['action'] == 'undo':
            _write_json(history, {'undo_id': journal['operation_id'], 'items': []})
        else:
            _write_json(history, journal)
    except OperationCancelled:
        try:
            _remove_copies(journal)
            pending.unlink()
            return {
                'ok': False, 'cancelled': True, 'recovery_required': False,
                'message': '已取消复制，本次生成的临时文件和副本已清理，原文件未改变。', 'count': 0}
        except Exception as rollback_error:
            return {
                'ok': False, 'cancelled': True, 'recovery_required': True,
                'message': f'复制已停止，但清理尚未完成。恢复记录已保留；请点击“恢复中断操作”：{rollback_error}',
                'count': 0}
    except Exception as exc:
        try:
            if journal['mode'] == 'rename':
                _recover_moves(journal)
            else:
                _remove_copies(journal)
            pending.unlink()
            return {'ok': False, 'message': f'操作失败，文件已恢复：{exc}', 'count': 0}
        except Exception as rollback_error:
            return {'ok': False, 'message': f'操作未完成：{exc}\n恢复记录已保留；请点击“恢复中断操作”：{rollback_error}', 'count': 0}
    try:
        pending.unlink()
    except OSError:
        return {'ok': True, 'message': '操作已完成，恢复记录待清理；请点击“恢复中断操作”。', 'count': len(items)}
    return {'ok': True, 'message': f'已完成 {len(items)} 个文件。', 'count': len(items)}


@_exclusive
def execute_plan(plan, progress=None, cancel_event=None):
    try:
        if any(x.status.startswith(('冲突', '错误')) for x in plan):
            raise ValueError('请先解决或跳过预览中的冲突和错误')
        items = [x for x in plan if x.status in {'可执行', '可重命名'}]
        if not items:
            raise ValueError('没有可执行的文件')
        if pending_operation():
            raise ValueError('存在未完成操作，请先点击“恢复中断操作”')
        modes = {x.mode for x in items}
        if len(modes) != 1 or not modes <= {'rename', 'copy'}:
            raise ValueError('操作模式不一致')
        mode = modes.pop()
        sources = {os.path.normcase(os.path.abspath(x.old_path)) for x in items}
        targets = set()
        if len(sources) != len(items):
            raise ValueError('源文件重复')
        for item in items:
            src, dst = Path(item.old_path), Path(item.new_path)
            target = os.path.normcase(os.path.abspath(dst))
            if target in targets or (dst.exists() and (mode == 'copy' or target not in sources)):
                raise ValueError(f'目标被占用或重复：{dst}')
            if src.is_symlink() or not src.is_file():
                raise ValueError(f'源文件不存在或为符号链接：{src}')
            if item.signature and not _matches(src, item.signature):
                raise ValueError(f'预览后文件发生改变，请刷新：{src}')
            targets.add(target)
        identities = {tuple(fingerprint(x.old_path)[:2]) for x in items}
        if len(identities) != len(items):
            raise ValueError('同一批次包含指向相同内容的硬链接，请分批处理')
        journal = _make_journal([(x.old_path, x.new_path) for x in items], mode)
        return _run(journal, progress, cancel_event)
    except Exception as exc:
        return {'ok': False, 'message': f'未执行操作：{exc}', 'count': 0}


@_exclusive
def undo_last():
    try:
        pending, history = _paths()
        if pending.exists():
            raise ValueError('请先恢复中断操作')
        if not history.exists() or not (data := _read(history)).get('items'):
            raise ValueError('没有可撤销的操作')
        items = data['items']
        for rec in items:
            expected = rec['signature'] if data['mode'] == 'rename' else rec['copy_signature']
            if not _matches(rec['dst'], expected):
                raise ValueError(f'文件已改变或丢失，未执行撤销：{rec["dst"]}')
        if data['mode'] == 'copy':
            journal = dict(data, action='undo', operation_id=uuid.uuid4().hex)
            _reserve_journal(pending, journal)
            _remove_copies(journal)
            _write_json(history, {'undo_id': journal['operation_id'], 'items': []})
            pending.unlink()
            return {'ok': True, 'message': f'已删除本次产生的 {len(items)} 个副本，原文件保留。', 'count': len(items)}
        current = {os.path.normcase(r['dst']) for r in items}
        for rec in items:
            if Path(rec['src']).exists() and os.path.normcase(rec['src']) not in current:
                raise ValueError(f'原文件名被占用：{rec["src"]}')
        return _run(_make_journal([(r['dst'], r['src']) for r in items], 'rename', 'undo'))
    except Exception as exc:
        return {'ok': False, 'message': f'撤销未完成：{exc}', 'count': 0}
