from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Optional

VIDEO_EXTS = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.ts', '.m2ts', '.webm'}
SUB_EXTS = {'.ass', '.ssa', '.srt', '.vtt', '.sup', '.sub'}
MEDIA_EXTS = VIDEO_EXTS | SUB_EXTS

LANG_TAGS = [
    'zh-hans', 'zh-hant', 'zh-cn', 'zh-tw', 'chs', 'cht', 'sc', 'tc',
    'jpn', 'jp', 'eng', 'en', 'chi', 'zho', '简中', '繁中', '简体', '繁体'
]

EXTRA_PATTERNS = [
    ('NCOP', re.compile(r'(?i)(?:^|[\s._\-\[\(])NC\s*OP(?:$|[\s._\-\]\)])')),
    ('NCED', re.compile(r'(?i)(?:^|[\s._\-\[\(])NC\s*ED(?:$|[\s._\-\]\)])')),
    ('OVA', re.compile(r'(?i)(?:^|[\s._\-\[\(])OVA(?:\s*0*(\d+))?(?:$|[\s._\-\]\)])')),
    ('OAD', re.compile(r'(?i)(?:^|[\s._\-\[\(])OAD(?:\s*0*(\d+))?(?:$|[\s._\-\]\)])')),
    ('SP', re.compile(r'(?i)(?:^|[\s._\-\[\(])(?:SP|SPECIAL)(?:\s*0*(\d+))?(?:$|[\s._\-\]\)])')),
    ('PV', re.compile(r'(?i)(?:^|[\s._\-\[\(])PV(?:\s*0*(\d+))?(?:$|[\s._\-\]\)])')),
]

@dataclass
class Detection:
    episode: Optional[int] = None
    confidence: int = 0
    reason: str = ''
    special: Optional[str] = None
    special_index: Optional[int] = None

@dataclass
class RenameItem:
    old_path: str
    new_path: str
    kind: str
    detected: str
    confidence: int
    status: str
    episode: Optional[int] = None
    special: Optional[str] = None


def natural_key(text: str):
    parts = re.split(r'(\d+)', text.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def _valid_episode(n: int) -> bool:
    # Do not blacklist values such as 8/10/12/24/60: they are valid episode numbers.
    # Technical numbers are filtered by their surrounding text instead.
    return 0 < n <= 9999


_TECHNICAL_TOKEN_PATTERNS = [
    # Video codecs. These are the most dangerous because the trailing 264/265/266
    # otherwise look exactly like a valid episode number.
    re.compile(r'(?i)(?<![A-Za-z0-9])(?:x|h)\s*26[456](?!\d)'),
    re.compile(r'(?i)(?<![A-Za-z0-9])(?:AVC|HEVC|H\.26[456]|X\.26[456])(?![A-Za-z0-9])'),
    re.compile(r'(?i)(?<![A-Za-z0-9])(?:AV1|VP8|VP9)(?![A-Za-z0-9])'),
    # Resolution / bit depth / frame rate / refresh rate / bit rate.
    re.compile(r'(?i)(?<!\d)\d{3,4}\s*[x×]\s*\d{3,4}(?!\d)'),
    re.compile(r'(?i)(?<!\d)\d{3,4}\s*[pi](?![A-Za-z])'),
    re.compile(r'(?i)(?<!\d)\d+(?:\.\d+)?\s*(?:bit|fps|hz|kbps|mbps)(?![A-Za-z])'),
]


def _strip_technical_tokens(stem: str) -> str:
    """Remove common release technical parameters before generic number matching.

    Explicit episode forms (S01E03 / E03 / 第3集 / [03]) are parsed from the
    original stem first. Generic trailing/standalone-number rules use this cleaned
    string so x265, h264, 1080p, 10bit, 23.976fps, etc. cannot outrank a real
    episode candidate.
    """
    cleaned = stem
    for pat in _TECHNICAL_TOKEN_PATTERNS:
        cleaned = pat.sub(' ', cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()


def detect_language_suffix(stem: str) -> str:
    low = stem.lower()
    for tag in LANG_TAGS:
        t = tag.lower()
        # Prefer delimiter-bounded language tags.
        if re.search(rf'(?i)(?:^|[. _\-\[\(]){re.escape(t)}(?:$|[. _\-\]\)])', low):
            normalized = tag
            if normalized in {'简中', '简体'}:
                return 'zh-Hans'
            if normalized in {'繁中', '繁体'}:
                return 'zh-Hant'
            return normalized
    return ''


def detect_episode(filename: str) -> Detection:
    stem = Path(filename).stem.strip()

    # Pure numeric file names are very common in anime folders: 01.mkv, 002.ass, etc.
    # Give them the highest regular-episode confidence so mixed folders work reliably.
    m = re.fullmatch(r'0*(\d{1,4})', stem)
    if m:
        try:
            n = int(m.group(1))
        except ValueError:
            n = 0
        if _valid_episode(n):
            return Detection(episode=n, confidence=100, reason='纯数字文件名')

    for special, pat in EXTRA_PATTERNS:
        m = pat.search(stem)
        if m:
            idx = None
            if m.lastindex and m.group(1):
                try:
                    idx = int(m.group(1))
                except ValueError:
                    pass
            return Detection(confidence=98, reason=special, special=special, special_index=idx)

    candidates: list[tuple[int, int, str]] = []

    def add(score: int, raw: str, reason: str):
        try:
            n = int(raw)
        except (TypeError, ValueError):
            return
        if _valid_episode(n):
            candidates.append((score, n, reason))

    # S01E03 / S1.E3
    for m in re.finditer(r'(?i)(?:^|[^A-Z0-9])S\s*0*\d{1,2}\s*[._\- ]*E(?:P(?:ISODE)?)?\s*0*(\d{1,4})(?:v\d+)?(?:\b|[^0-9])', stem):
        add(100, m.group(1), 'SxxEyy')

    # E03 / EP03 / Episode 03
    for m in re.finditer(r'(?i)(?:^|[^A-Z0-9])E(?:P(?:ISODE)?)?\s*[._\- ]*0*(\d{1,4})(?:v\d+)?(?:\b|[^0-9])', stem):
        add(97, m.group(1), 'E/EP')

    # Chinese/Japanese episode words.
    for m in re.finditer(r'(?:第\s*)?(\d{1,4})\s*(?:集|话|話|回)', stem):
        add(99, m.group(1), '第xx集/话')

    # [03], (03), 【03】. Penalize codec/resolution-like bracket contents.
    for m in re.finditer(r'[\[\(【]\s*0*(\d{1,4})(?:v\d+)?\s*[\]\)】]', stem):
        add(88, m.group(1), '[xx]')

    generic_stem = _strip_technical_tokens(stem)

    # Common release naming: " - 03 ", "_03_", ".03."
    for m in re.finditer(r'(?:^|\s[-–—]\s|[._])0*(\d{1,4})(?:v\d+)?(?=$|[\s._\-\[])', generic_stem):
        add(82, m.group(1), '分隔数字')

    # Title immediately followed by an episode number, e.g. 未来日记01 / MiraiNikki02.
    # Restrict this to the end of the stem to avoid treating codec/resolution numbers as episodes.
    m = re.search(r'(?<!\d)0*(\d{1,4})(?:v\d+)?$', generic_stem)
    if m and m.start() > 0:
        add(90, m.group(1), '末尾集数')

    # Standalone 1-3 digit token. Reject likely technical values/year-adjacent values.
    for m in re.finditer(r'(?<!\d)(\d{1,3})(?!\d)', generic_stem):
        raw = m.group(1)
        add(55, raw, '独立数字')

    if not candidates:
        return Detection(reason='未识别')

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score = candidates[0][0]
    best = [c for c in candidates if c[0] == best_score]
    # If top-confidence candidates disagree, flag as uncertain rather than guessing.
    unique_eps = {c[1] for c in best}
    if len(unique_eps) > 1:
        return Detection(confidence=25, reason='候选冲突')
    score, ep, reason = best[0]
    return Detection(episode=ep, confidence=score, reason=reason)


def format_name(template: str, title: str, season: int, episode: Optional[int], special: Optional[str] = None, special_index: Optional[int] = None) -> str:
    if special:
        idx = special_index or 1
        token = special if special in {'NCOP', 'NCED'} else f'{special}{idx:02d}'
        return f'{title} - {token}'
    if episode is None:
        raise ValueError('episode is required for regular episode')

    # Support {episode:02}, {season:02}, and simple placeholders.
    values = {'title': title, 'season': season, 'episode': episode}
    try:
        return template.format(**values)
    except Exception:
        # Safe fallback.
        return f'{title} - {episode:02d}'


def _iter_files(folder: Path, recursive: bool) -> Iterable[Path]:
    it = folder.rglob('*') if recursive else folder.iterdir()
    for p in it:
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS:
            yield p


def build_plan(
    folder: str,
    title: str,
    season: int,
    template: str,
    recursive: bool = False,
    rename_subtitles: bool = True,
    preserve_language: bool = True,
    force_sequence: bool = False,
    sequence_start: int = 1,
) -> list[RenameItem]:
    root = Path(folder)
    files = sorted(_iter_files(root, recursive), key=lambda p: natural_key(str(p.relative_to(root))))

    videos = [p for p in files if p.suffix.lower() in VIDEO_EXTS]
    forced_map: dict[str, int] = {}
    if force_sequence:
        ep = max(1, sequence_start)
        for p in videos:
            # Specials keep their special classification and don't consume main episode numbers.
            det = detect_episode(p.name)
            if det.special:
                continue
            forced_map[str(p)] = ep
            ep += 1

    # Map each video to both its original detected episode and its final episode.
    # In forced numbering mode subtitles must follow the video's FINAL number,
    # even when the subtitle itself confidently contains the old episode number.
    video_assoc: list[tuple[str, Optional[int], int]] = []
    for p in videos:
        det = detect_episode(p.name)
        ep = forced_map.get(str(p), det.episode)
        if ep is not None:
            video_assoc.append((p.stem.lower(), det.episode, ep))

    plan: list[RenameItem] = []
    proposed_targets: dict[str, int] = {}

    for p in files:
        kind = '视频' if p.suffix.lower() in VIDEO_EXTS else '字幕'
        if kind == '字幕' and not rename_subtitles:
            continue

        det = detect_episode(p.name)
        ep = det.episode
        special = det.special
        special_index = det.special_index

        if force_sequence and kind == '视频' and not special:
            ep = forced_map.get(str(p))
            if ep is not None:
                det = Detection(episode=ep, confidence=100, reason='强制排序编号')

        if kind == '字幕' and not special:
            low = p.stem.lower()

            # First choice: filename/base-name association. This also handles
            # language suffixes such as Show.E03.chs.ass.
            stem_matches = [
                (base, final_ep)
                for base, _original_ep, final_ep in video_assoc
                if low == base
                or low.startswith(base + '.')
                or low.startswith(base + '_')
                or low.startswith(base + '-')
            ]
            associated_ep: Optional[int] = None
            if stem_matches:
                stem_matches.sort(key=lambda x: len(x[0]), reverse=True)
                associated_ep = stem_matches[0][1]

            # Second choice: if the subtitle has an episode number, match it to
            # a UNIQUE video's original episode number. This covers filenames
            # such as "03.ass" paired with "Show E03.mkv".
            if associated_ep is None and det.episode is not None:
                episode_matches = {
                    final_ep
                    for _base, original_ep, final_ep in video_assoc
                    if original_ep == det.episode
                }
                if len(episode_matches) == 1:
                    associated_ep = next(iter(episode_matches))

            # Forced numbering always follows the associated video. In normal
            # mode, preserve a confident subtitle number and only use association
            # as a fallback for uncertain/unrecognized subtitles.
            if associated_ep is not None and (force_sequence or ep is None or det.confidence < 70):
                ep = associated_ep
                det = Detection(episode=ep, confidence=95, reason='关联视频')

        if ep is None and not special:
            plan.append(RenameItem(str(p), str(p), kind, det.reason or '未识别', det.confidence, '未识别，跳过'))
            continue

        base = format_name(template, title, season, ep, special, special_index)
        if kind == '字幕' and preserve_language:
            lang = detect_language_suffix(p.stem)
            if lang:
                base += f'.{lang}'

        target = p.with_name(base + p.suffix.lower())
        status = '可重命名'
        if target.name == p.name:
            status = '无需修改'

        key = os.path.normcase(os.path.abspath(str(target)))
        proposed_targets[key] = proposed_targets.get(key, 0) + 1
        plan.append(RenameItem(
            old_path=str(p), new_path=str(target), kind=kind,
            detected=(special or (f'第 {ep} 集' if ep is not None else det.reason)),
            confidence=det.confidence, status=status,
            episode=ep, special=special,
        ))

    # Second pass: conflicts / existing unrelated targets.
    old_norm = {os.path.normcase(os.path.abspath(x.old_path)) for x in plan}
    for item in plan:
        if item.status in {'未识别，跳过', '无需修改'}:
            continue
        target_key = os.path.normcase(os.path.abspath(item.new_path))
        if proposed_targets.get(target_key, 0) > 1:
            item.status = '冲突：多个文件目标同名'
            continue
        target = Path(item.new_path)
        if target.exists() and target_key not in old_norm:
            item.status = '冲突：目标已存在'

    return plan


def _history_path() -> Path:
    base = os.environ.get('LOCALAPPDATA')
    if base:
        p = Path(base) / 'AnimeRenamer'
    else:
        p = Path.home() / '.anime_renamer'
    p.mkdir(parents=True, exist_ok=True)
    return p / 'rename_history.json'


def _norm_path(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _transactional_rename(pairs: list[tuple[Path, Path]], temp_prefix: str) -> tuple[bool, str]:
    """Rename a batch atomically enough for local filesystem use.

    Every source is first moved to a unique temporary path, then every temporary
    path is moved to its destination. If either phase fails, all files that have
    moved are staged again and restored to their original source names. The
    second staging step is important for chains such as A->B, B->C.
    """
    records: list[dict] = []
    try:
        # Phase 1: vacate every source name so destination chains cannot collide.
        for src, dst in pairs:
            tmp = src.with_name(f'{temp_prefix}{uuid.uuid4().hex}{src.suffix}')
            os.replace(src, tmp)
            records.append({'src': src, 'dst': dst, 'tmp': tmp, 'location': 'tmp'})

        # Phase 2: publish final names.
        for rec in records:
            rec['dst'].parent.mkdir(parents=True, exist_ok=True)
            os.replace(rec['tmp'], rec['dst'])
            rec['location'] = 'dst'
        return True, ''

    except Exception as exc:
        rollback_errors: list[str] = []
        staged: list[tuple[dict, Path]] = []

        # Stage every moved file away from both source and destination names.
        # This prevents a restored B from blocking restoration of A in A->B,B->C.
        for rec in records:
            current = rec['dst'] if rec['location'] == 'dst' else rec['tmp']
            try:
                if current.exists():
                    rollback_tmp = current.with_name(
                        f'.__anime_renamer_rollback_{uuid.uuid4().hex}{current.suffix}'
                    )
                    os.replace(current, rollback_tmp)
                    staged.append((rec, rollback_tmp))
            except Exception as rb_exc:
                rollback_errors.append(f'{current}: {rb_exc}')

        # Restore original source names.
        for rec, rollback_tmp in staged:
            try:
                rec['src'].parent.mkdir(parents=True, exist_ok=True)
                os.replace(rollback_tmp, rec['src'])
            except Exception as rb_exc:
                rollback_errors.append(f'{rollback_tmp} -> {rec["src"]}: {rb_exc}')

        if rollback_errors:
            return False, f'{exc}；回滚仍有异常：' + ' | '.join(rollback_errors)
        return False, str(exc)


def execute_plan(plan: list[RenameItem]) -> dict:
    actionable = [x for x in plan if x.status == '可重命名']
    if not actionable:
        return {'ok': False, 'message': '没有可执行的重命名项目。', 'count': 0}

    # Recheck conflicts immediately before modifying anything.
    old_set = {_norm_path(x.old_path) for x in actionable}
    target_set: set[str] = set()
    for x in actionable:
        t = _norm_path(x.new_path)
        if t in target_set:
            return {'ok': False, 'message': f'目标文件名冲突：{x.new_path}', 'count': 0}
        target_set.add(t)
        if Path(x.new_path).exists() and t not in old_set:
            return {'ok': False, 'message': f'目标文件已存在：{x.new_path}', 'count': 0}

    pairs = [(Path(x.old_path), Path(x.new_path)) for x in actionable]
    ok, error = _transactional_rename(pairs, '.__anime_renamer_')
    if not ok:
        return {'ok': False, 'message': f'重命名失败，已回滚：{error}', 'count': 0}

    completed = [{'old_path': x.old_path, 'new_path': x.new_path} for x in actionable]

    history = {
        'version': 1,
        'operation_id': uuid.uuid4().hex,
        'items': completed,
    }
    _history_path().write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'ok': True, 'message': f'已重命名 {len(completed)} 个文件。', 'count': len(completed)}


def undo_last() -> dict:
    hp = _history_path()
    if not hp.exists():
        return {'ok': False, 'message': '没有找到可撤销的历史记录。', 'count': 0}
    try:
        history = json.loads(hp.read_text(encoding='utf-8'))
        items = history.get('items', [])
    except Exception as e:
        return {'ok': False, 'message': f'历史记录读取失败：{e}', 'count': 0}

    if not items:
        return {'ok': False, 'message': '历史记录为空。', 'count': 0}

    # Validate first. An old name occupied by another CURRENT file from this same
    # batch is legal (e.g. original A->B, B->C leaves B and C before undo).
    current_new_set = {_norm_path(rec['new_path']) for rec in items}
    for rec in items:
        oldp = Path(rec['old_path'])
        newp = Path(rec['new_path'])
        if not newp.exists():
            return {'ok': False, 'message': f'无法撤销：当前文件不存在：{newp}', 'count': 0}
        if oldp.exists() and _norm_path(oldp) not in current_new_set:
            return {'ok': False, 'message': f'无法撤销：原文件名已被占用：{oldp}', 'count': 0}

    pairs = [(Path(rec['new_path']), Path(rec['old_path'])) for rec in items]
    ok, error = _transactional_rename(pairs, '.__anime_renamer_undo_')
    if not ok:
        return {'ok': False, 'message': f'撤销失败，已恢复到撤销前状态：{error}', 'count': 0}

    hp.unlink(missing_ok=True)
    return {'ok': True, 'message': f'已撤销上一次操作，共恢复 {len(items)} 个文件。', 'count': len(items)}
