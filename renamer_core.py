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

BAD_NUMBERS = {
    264, 265, 266, 480, 576, 720, 1080, 1440, 2160, 4320,
    8, 10, 12, 16, 24, 25, 30, 50, 60, 120,
}

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
    return 0 < n <= 999 and n not in BAD_NUMBERS


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
    stem = Path(filename).stem

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
    for m in re.finditer(r'(?i)(?:^|[^A-Z0-9])S\s*0*\d{1,2}\s*[._\- ]*E(?:P(?:ISODE)?)?\s*0*(\d{1,3})(?:v\d+)?(?:\b|[^0-9])', stem):
        add(100, m.group(1), 'SxxEyy')

    # E03 / EP03 / Episode 03
    for m in re.finditer(r'(?i)(?:^|[^A-Z0-9])E(?:P(?:ISODE)?)?\s*[._\- ]*0*(\d{1,3})(?:v\d+)?(?:\b|[^0-9])', stem):
        add(97, m.group(1), 'E/EP')

    # Chinese/Japanese episode words.
    for m in re.finditer(r'(?:第\s*)?(\d{1,3})\s*(?:集|话|話|回)', stem):
        add(99, m.group(1), '第xx集/话')

    # [03], (03), 【03】. Penalize codec/resolution-like bracket contents.
    for m in re.finditer(r'[\[\(【]\s*0*(\d{1,3})(?:v\d+)?\s*[\]\)】]', stem):
        add(88, m.group(1), '[xx]')

    # Common release naming: " - 03 ", "_03_", ".03."
    for m in re.finditer(r'(?:^|\s[-–—]\s|[._])0*(\d{1,3})(?:v\d+)?(?=$|[\s._\-\[])', stem):
        add(82, m.group(1), '分隔数字')

    # Standalone 1-3 digit token. Reject likely technical values/year-adjacent values.
    for m in re.finditer(r'(?<!\d)(\d{1,3})(?!\d)', stem):
        raw = m.group(1)
        n = int(raw)
        left = stem[max(0, m.start()-6):m.start()].lower()
        right = stem[m.end():m.end()+8].lower()
        if any(x in right for x in ('p', 'bit', 'fps', 'hz')):
            continue
        if any(x in left for x in ('x26', 'h26', 'hevc', 'avc')):
            continue
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

    # Map video base names to episode for subtitle association.
    video_assoc: list[tuple[str, int]] = []
    for p in videos:
        det = detect_episode(p.name)
        ep = forced_map.get(str(p), det.episode)
        if ep is not None:
            video_assoc.append((p.stem.lower(), ep))

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
            # If subtitle itself is uncertain, associate it with a video's stem.
            if ep is None or det.confidence < 70:
                low = p.stem.lower()
                matches = [(base, vep) for base, vep in video_assoc if low == base or low.startswith(base + '.') or low.startswith(base + '_') or low.startswith(base + '-')]
                if matches:
                    matches.sort(key=lambda x: len(x[0]), reverse=True)
                    ep = matches[0][1]
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


def execute_plan(plan: list[RenameItem]) -> dict:
    actionable = [x for x in plan if x.status == '可重命名']
    if not actionable:
        return {'ok': False, 'message': '没有可执行的重命名项目。', 'count': 0}

    # Recheck conflicts immediately before modifying anything.
    old_set = {os.path.normcase(os.path.abspath(x.old_path)) for x in actionable}
    target_set: set[str] = set()
    for x in actionable:
        t = os.path.normcase(os.path.abspath(x.new_path))
        if t in target_set:
            return {'ok': False, 'message': f'目标文件名冲突：{x.new_path}', 'count': 0}
        target_set.add(t)
        if Path(x.new_path).exists() and t not in old_set:
            return {'ok': False, 'message': f'目标文件已存在：{x.new_path}', 'count': 0}

    temp_records = []
    completed = []
    try:
        # Phase 1: move all sources to temporary names to avoid A->B / B->C collisions.
        for x in actionable:
            src = Path(x.old_path)
            tmp = src.with_name(f'.__anime_renamer_{uuid.uuid4().hex}{src.suffix}')
            os.replace(src, tmp)
            temp_records.append((x, tmp))

        # Phase 2: move temp files to final targets.
        for x, tmp in temp_records:
            dst = Path(x.new_path)
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.replace(tmp, dst)
            completed.append({'old_path': x.old_path, 'new_path': x.new_path})

    except Exception as e:
        # Best-effort rollback.
        for x, tmp in reversed(temp_records):
            try:
                if tmp.exists() and not Path(x.old_path).exists():
                    os.replace(tmp, x.old_path)
            except Exception:
                pass
        for rec in reversed(completed):
            try:
                newp = Path(rec['new_path'])
                oldp = Path(rec['old_path'])
                if newp.exists() and not oldp.exists():
                    os.replace(newp, oldp)
            except Exception:
                pass
        return {'ok': False, 'message': f'重命名失败，已尝试回滚：{e}', 'count': len(completed)}

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

    # Validate first.
    for rec in items:
        oldp = Path(rec['old_path'])
        newp = Path(rec['new_path'])
        if not newp.exists():
            return {'ok': False, 'message': f'无法撤销：当前文件不存在：{newp}', 'count': 0}
        if oldp.exists():
            return {'ok': False, 'message': f'无法撤销：原文件名已被占用：{oldp}', 'count': 0}

    temp_records = []
    try:
        for rec in items:
            newp = Path(rec['new_path'])
            tmp = newp.with_name(f'.__anime_renamer_undo_{uuid.uuid4().hex}{newp.suffix}')
            os.replace(newp, tmp)
            temp_records.append((rec, tmp))
        for rec, tmp in temp_records:
            oldp = Path(rec['old_path'])
            oldp.parent.mkdir(parents=True, exist_ok=True)
            os.replace(tmp, oldp)
    except Exception as e:
        return {'ok': False, 'message': f'撤销失败：{e}', 'count': 0}

    hp.unlink(missing_ok=True)
    return {'ok': True, 'message': f'已撤销上一次操作，共恢复 {len(items)} 个文件。', 'count': len(items)}
