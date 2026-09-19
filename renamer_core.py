"""Offline detection and preview planning. Never changes media files."""
from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

from file_operations import execute_plan, undo_last, recover_pending, pending_operation

VERSION = '0.3.0'
VIDEO_EXTS = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.ts', '.m2ts', '.webm'}
SUB_EXTS = {'.ass', '.ssa', '.srt', '.vtt', '.sup', '.sub', '.idx'}
LANG_TAGS = ['zh-hans', 'zh-hant', 'zh-cn', 'zh-tw', 'chs', 'cht', 'sc', 'tc',
             'jpn', 'jp', 'eng', 'en', 'chi', 'zho', '简中', '繁中', '简体', '繁体']
READY = '可执行'


@dataclass
class Detection:
    episode: int | str | None = None
    confidence: int = 0
    reason: str = '未识别'
    special: str | None = None
    special_index: int | None = None
    season: int | None = None


@dataclass
class GroupSettings:
    title: str = ''
    season: int | None = None
    start: int | None = None


@dataclass
class RenameItem:
    old_path: str
    new_path: str
    kind: str
    detected: str
    confidence: int
    status: str
    episode: int | str | None = None
    special: str | None = None
    group: str = ''
    group_id: str = ''
    reason: str = ''
    signature: tuple = ()
    mode: str = 'rename'


def natural_key(text):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', str(text).lower())]


def _number(raw):
    whole, dot, fractional = raw.partition('.')
    number = int(whole)
    if not 0 <= number <= 9999:
        raise ValueError('集数须在 0–9999 之间')
    if dot:
        fractional = fractional.rstrip('0')
    return f'{number}.{fractional}' if fractional else number


def parse_override(text):
    """Accept 03, 12.5, E03, NCOP02 or SP01."""
    text = text.strip().upper()
    m = re.fullmatch(r'(NCOP|NCED|OVA|OAD|SP|PV)\s*(\d{1,4})?', text)
    if m:
        return Detection(confidence=100, reason='手动纠正', special=m[1],
                         special_index=int(m[2] or 1))
    m = re.fullmatch(r'(?:E|EP)?(\d{1,4}(?:\.\d{1,3})?)', text)
    if not m:
        raise ValueError('请输入集数（如 03、12.5）或特别篇编号（如 SP01、NCOP02）')
    return Detection(episode=_number(m[1]), confidence=100, reason='手动纠正')


def detect_language_suffix(stem):
    for tag in LANG_TAGS:
        if re.search(rf'(?i)(?:^|[. _\-\[(]){re.escape(tag)}(?:$|[. _\-\])])', stem):
            return {'简中': 'zh-Hans', '简体': 'zh-Hans', '繁中': 'zh-Hant',
                    '繁体': 'zh-Hant'}.get(tag, tag)
    return ''


def _clean(stem):
    patterns = [
        r'(?<![A-Za-z0-9])(?:[xh][ .]*26[456]|AV1|VP[89]|HEVC|AVC)(?!\d)',
        r'(?<!\d)\d{3,4}\s*[x×]\s*\d{3,4}(?!\d)',
        r'(?<!\d)\d{3,4}\s*[pi](?![A-Za-z])',
        r'(?<!\d)\d+(?:\.\d+)?\s*(?:bit|fps|hz|kbps|mbps)(?![A-Za-z])',
        r'(?:AAC|FLAC|DDP|DD|DTS|AC3|EAC3|TRUEHD)[ ._-]*(?:\d\.\d)?',
        r'(?<![A-Za-z0-9])(?:2\.0|5\.1|7\.1)(?!\d)',
        r'[\[(](?:480|576|720|1080|1440|2160|4320)[\])]',
        r'[\[(](?:19|20)\d{2}[\])]',
        r'[\[(][A-Fa-f0-9]{8}[\])]',
    ]
    for pattern in patterns:
        stem = re.sub(pattern, ' ', stem, flags=re.I)
    return stem.strip()


def detect_episode(filename):
    stem = Path(filename).stem.strip()
    if re.fullmatch(r'\d{1,4}(?:\.\d{1,3})?', stem):
        return Detection(_number(stem), 100, '纯数字文件名')
    season = re.search(r'(?i)(?<![A-Z0-9])S(\d{1,2})[ ._-]*E', stem)
    season_no = int(season[1]) if season else None
    special = re.search(r'(?i)(?:^|[\s._\-\[（(【])'
                        r'(NC\s*OP|NC\s*ED|OVA|OAD|SP|SPECIAL|PV)'
                        r'[ _-]*(\d{1,4})?(?=$|[\s._\-\]）)】])', stem)
    if special:
        kind = re.sub(r'\s', '', special[1].upper()).replace('SPECIAL', 'SP')
        return Detection(confidence=98, reason='特别篇', special=kind,
                         special_index=int(special[2]) if special[2] else None,
                         season=season_no)
    cleaned = _clean(stem)
    if re.search(r'(?i)(?:E|EP|[\s\[])(\d{1,4})\s*[-~&]\s*(?:E)?\d{1,4}', cleaned):
        return Detection(reason='多集文件，请手动确认', season=season_no)
    number = r'(\d{1,4}(?:\.\d{1,3})?)'
    end = r'(?:v\d+)?(?!\d|\.\d)'
    candidates = []
    rules = [
        (100, rf'(?i)(?<![A-Z0-9])S\d{{1,2}}[ ._-]*E\s*{number}{end}', '季集编号'),
        (97, rf'(?i)(?<![A-Z0-9])E(?:P(?:ISODE)?)?[ ._-]*{number}{end}', '集数标记'),
        (99, rf'(?:第\s*)?{number}\s*(?:集|话|話|回)', '中文集数'),
        (88, rf'[\[(【]\s*{number}(?:v\d+)?\s*[\])】]', '括号集数'),
        (85, rf'(?:^|\s[-–—]\s|[._]){number}{end}(?=$|[\s._\-\[])', '分隔集数'),
        (80, rf'(?<![\d.]){number}(?:v\d+)?$', '末尾集数'),
    ]
    for score, pattern, reason in rules:
        for match in re.finditer(pattern, cleaned):
            candidates.append((score, _number(match[1]), reason))
    if not candidates:
        for match in re.finditer(r'(?<![\d.])(\d{1,3})(?![\d.])', cleaned):
            candidates.append((55, int(match[1]), '独立数字，请确认'))
    if not candidates:
        return Detection(season=season_no)
    best = max(c[0] for c in candidates)
    top = [c for c in candidates if c[0] == best]
    if len({c[1] for c in top}) != 1:
        return Detection(confidence=25, reason='多个集数候选，请确认', season=season_no)
    score, ep, reason = top[0]
    return Detection(ep, score, reason, season=season_no)


class _Episode:
    def __init__(self, value):
        self.value = str(value)

    def __format__(self, spec):
        whole, dot, fraction = self.value.partition('.')
        return format(int(whole), spec) + (dot + fraction if dot else '')


def validate_name(name):
    if not name or name in {'.', '..'} or re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
        raise ValueError('文件名为空或包含 Windows 不允许的字符')
    if name.endswith((' ', '.')) or len(name) > 240:
        raise ValueError('文件名过长，或以空格／句点结尾')
    if re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', name):
        raise ValueError('不能使用 Windows 保留文件名')
    return name


def format_name(template, title, season, episode, special=None, special_index=None):
    if special:
        token = special + (f'{special_index:02d}' if special_index is not None else '')
        return validate_name(f'{title} - {token}')
    if episode is None:
        raise ValueError('缺少集数')
    try:
        result = template.format(title=title, season=season, episode=_Episode(episode))
    except (KeyError, ValueError, AttributeError, IndexError) as exc:
        raise ValueError('模板无效，仅支持 title、season、episode 字段') from exc
    return validate_name(result)


def _signature(path):
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)


def _iter_files(root, recursive):
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()
                   and not getattr(Path(directory) / d, 'is_junction', lambda: False)()]
        for name in files:
            p = Path(directory) / name
            if name.startswith(('.__anime_renamer_', '.__anime_recovery_')):
                continue
            if p.suffix.lower() in VIDEO_EXTS | SUB_EXTS and not p.is_symlink():
                yield p
        if not recursive:
            break


def build_plan(folder, title, season, template, recursive=False, rename_subtitles=True,
               preserve_language=True, force_sequence=False, sequence_start=1,
               group_settings=None, overrides=None, skipped=None,
               mode='rename', output_folder=''):
    root = Path(folder).resolve()
    if not root.is_dir():
        raise ValueError('请选择有效的输入文件夹')
    if mode not in {'rename', 'copy'}:
        raise ValueError('未知操作模式')
    if not 1 <= sequence_start <= 9999:
        raise ValueError('起始集数须在 1–9999 之间')
    output = Path(output_folder).resolve() if output_folder else None
    if mode == 'copy' and (output is None or output == root or root in output.parents):
        raise ValueError('复制目标必须在输入文件夹之外，避免再次导入已整理文件')
    groups, overrides, skipped = group_settings or {}, overrides or {}, set(skipped or [])
    paths = sorted(_iter_files(root, recursive), key=lambda p: natural_key(p.relative_to(root)))
    if not rename_subtitles:
        paths = [p for p in paths if p.suffix.lower() in VIDEO_EXTS]
    originals = {p: detect_episode(p.name) for p in paths}
    detections = {p: replace(originals[p]) for p in paths}
    for p in paths:
        if str(p) in overrides:
            detections[p] = replace(parse_override(overrides[str(p)]), season=originals[p].season)
    videos = [p for p in paths if p.suffix.lower() in VIDEO_EXTS]
    video_set = set(videos)

    # Subtitle association used to rescan the complete video list for every subtitle,
    # which made large single-directory libraries approach O(subtitles * videos).
    # Build directory/name/episode indexes once so each subtitle only performs direct
    # dictionary lookups plus work proportional to its own file-name length.
    stems_by_parent = defaultdict(lambda: defaultdict(list))
    episodes_by_parent = defaultdict(list)
    episodes_by_parent_season = defaultdict(list)
    for video in videos:
        stems_by_parent[video.parent][video.stem.lower()].append(video)
        det = originals[video]
        if det.episode is not None:
            episodes_by_parent[(video.parent, det.episode, det.special)].append(video)
            episodes_by_parent_season[(video.parent, det.episode, det.special, det.season)].append(video)

    associations, ambiguous = {}, set()
    for p in paths:
        if p in video_set:
            continue

        subtitle_stem = p.stem.lower()
        stem_index = stems_by_parent.get(p.parent, {})
        # Exact video stem or the longest video-stem prefix followed by . _ or -.
        # Trying candidates longest-first preserves the old longest-match behavior
        # without scanning every video in the directory.
        candidates = [subtitle_stem]
        candidates.extend(subtitle_stem[:i] for i, ch in enumerate(subtitle_stem)
                          if i and ch in '._-')
        matches = []
        for candidate in sorted(set(candidates), key=len, reverse=True):
            found = stem_index.get(candidate)
            if found:
                matches = list(found)
                break

        if not matches:
            sub = originals[p]
            if sub.episode is not None:
                if sub.season is None:
                    matches = list(episodes_by_parent.get(
                        (p.parent, sub.episode, sub.special), ()))
                else:
                    matches = list(episodes_by_parent_season.get(
                        (p.parent, sub.episode, sub.special, sub.season), ()))
        if len(matches) == 1:
            associations[p] = matches[0]
        elif len(matches) > 1:
            ambiguous.add(p)

    def group_for(p):
        det = originals[associations.get(p, p)]
        relative = p.parent.relative_to(root).as_posix()
        return f'{relative}|S{det.season if det.season is not None else "unknown"}', relative, det.season

    counters = {}
    if force_sequence:
        for p in videos:
            det = detections[p]
            if det.special or str(p) in overrides or str(p) in skipped:
                continue
            if isinstance(det.episode, str) or '多集' in det.reason:
                continue
            key, _, _ = group_for(p)
            options = groups.get(key, GroupSettings())
            ep = counters.get(key, options.start if options.start is not None else sequence_start)
            if not 1 <= ep <= 9999:
                raise ValueError('组内集数超出 1–9999 范围')
            detections[p] = replace(det, episode=ep, confidence=100, reason='组内排序编号')
            counters[key] = ep + 1

    plan = []
    for p in paths:
        key, relative, detected_season = group_for(p)
        options = groups.get(key, GroupSettings())
        item_title = options.title.strip() or title.strip()
        item_season = options.season if options.season is not None else (detected_season if detected_season is not None else season)
        if not 0 <= item_season <= 99:
            raise ValueError('季度须在 0–99 之间')
        det = detections[p]
        video = associations.get(p)
        if video and str(p) not in overrides:
            det = replace(detections[video], reason='跟随同目录视频')
        label = '当前目录' if relative == '.' else relative
        if detected_season is not None:
            label += f' / S{detected_season:02d}'
        status = READY
        if str(p) in skipped:
            status = '已跳过'
        elif video and str(video) in skipped:
            status = '已跳过：关联视频已跳过'
        elif p in ambiguous and str(p) not in overrides:
            status = '待确认：字幕匹配多个视频'
        elif force_sequence and p.suffix.lower() in SUB_EXTS and not video and str(p) not in overrides:
            status = '待确认：未找到对应视频'
        elif det.episode is None and not det.special:
            status = '待确认：' + det.reason
        elif det.confidence < 70:
            status = '待确认：低置信度'
        elif not item_title:
            status = '待填写名称'
        target = p
        if status == READY:
            try:
                base = format_name(template, item_title, item_season, det.episode,
                                   det.special, det.special_index)
                lang = detect_language_suffix(p.stem) if p.suffix.lower() in SUB_EXTS and preserve_language else ''
                name = validate_name(base + ('.' + lang if lang else '') + p.suffix.lower())
                target = (output / p.parent.relative_to(root) / name) if mode == 'copy' else p.with_name(name)
                if target == p and target.name == p.name:
                    status = '无需修改'
            except ValueError as exc:
                status = '错误：' + str(exc)
        token = (det.special + (str(det.special_index) if det.special_index is not None else '')) if det.special else str(det.episode)
        plan.append(RenameItem(str(p), str(target), '视频' if p in video_set else '字幕',
                               token if det.episode is not None or det.special else '—',
                               det.confidence, status, det.episode, det.special, label,
                               key, det.reason, _signature(p), mode))
    targets = Counter(os.path.normcase(x.new_path) for x in plan if x.status in {READY, '无需修改'})
    candidates = {os.path.normcase(x.old_path) for x in plan if x.status == READY}
    for item in plan:
        if item.status != READY:
            continue
        dst = os.path.normcase(item.new_path)
        if targets[dst] > 1:
            item.status = '冲突：目标同名'
        elif Path(item.new_path).exists() and (mode == 'copy' or dst not in candidates):
            item.status = '冲突：目标已存在'
    while True:
        moving = {os.path.normcase(x.old_path) for x in plan if x.status == READY}
        blocked = [x for x in plan if x.status == READY and Path(x.new_path).exists()
                   and os.path.normcase(x.new_path) not in moving]
        if not blocked:
            break
        for item in blocked:
            item.status = '冲突：目标被未执行文件占用'
    return plan
