"""Light-novel mode kept separate from anime episode parsing."""
from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import simpledialog, ttk

import renamer_core as core
from renamer_core import GroupSettings, READY
from ui_theme import ThemeToggle
from ui_dialogs import GroupDialog

BOOK_EXTS = {'.epub', '.mobi', '.azw3', '.pdf', '.txt', '.cbz'}

NOVEL_TEMPLATES = {
    '书名 - 第01卷': '{title} - 第{volume:02d}卷',
    '书名 01': '{title} {volume:02d}',
    '书名 Vol.01': '{title} Vol.{volume:02d}',
    '书名 - 01 - 卷标题': '{title} - {volume:02d} - {volume_title}',
    '书名 - 第01卷 上 卷标题': '{title} - 第{volume:02d}卷 {part} {volume_title}',
    '自定义': '{title} - 第{volume:02d}卷',
}


@dataclass
class BookDetection:
    volume: int | str | None = None
    confidence: int = 0
    reason: str = '未识别卷数'
    volume_title: str = ''
    part: str = ''
    series_title: str = ''


@dataclass
class BookRenameItem:
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
    volume: int | str | None = None
    volume_title: str = ''
    part: str = ''
    series_title: str = ''


class _VolumeNumber:
    def __init__(self, value):
        self.value = str(value)

    def __format__(self, spec):
        whole, dot, fraction = self.value.partition('.')
        return format(int(whole), spec) + (dot + fraction if dot else '')


def _number(raw):
    whole, dot, fractional = raw.partition('.')
    number = int(whole)
    if not 0 <= number <= 9999:
        raise ValueError('卷数须在 0–9999 之间')
    if dot:
        fractional = fractional.rstrip('0')
    return f'{number}.{fractional}' if fractional else number


def parse_book_override(text):
    raw = text.strip()
    for pattern in [
        r'(?i)^(?:VOL(?:UME)?\.?|V|EP\.?)\s*(\d{1,4}(?:\.\d{1,3})?)$',
        r'^第\s*(\d{1,4}(?:\.\d{1,3})?)\s*(?:卷|冊|册)$',
        r'^(\d{1,4}(?:\.\d{1,3})?)$',
    ]:
        m = re.fullmatch(pattern, raw)
        if m:
            return _number(m[1])
    raise ValueError('请输入卷数（如 03、V03、Vol.03、Ep.03 或 第3卷）')


def _strip_edition_tags(text):
    tag_words = r'(?:台版|日版|简中|繁中|简体|繁体|中文版|中译|WEB|EPUB|MOBI|AZW3|电子版|精校版|校对版)'
    previous = None
    while previous != text:
        previous = text
        text = re.sub(rf'^\s*[\[【(（]\s*{tag_words}\s*[\]】)）]\s*', '', text, flags=re.I)
    return text.strip()


def _remove_title_once(text, title):
    title = (title or '').strip()
    return re.sub(re.escape(title), ' ', text, count=1, flags=re.I).strip() if title else text


def _normalize_part(raw):
    token = re.sub(r'\s', '', raw or '')
    mapping = {
        '上册': '上', '上卷': '上', '上部': '上', '上篇': '上',
        '中册': '中', '中卷': '中', '中部': '中', '中篇': '中',
        '下册': '下', '下卷': '下', '下部': '下', '下篇': '下',
    }
    return mapping.get(token, token)


def _trim_book_text(text):
    text = _strip_edition_tags(text or '')
    text = re.sub(r'^[\s._\-–—·:：]+|[\s._\-–—·:：]+$', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _match_known_series(filename, known_titles):
    """Return the longest previously detected series title matching this file prefix."""
    stem = _strip_edition_tags(Path(filename).stem.strip())
    folded = stem.casefold()
    matches = [title for title in known_titles if title and folded.startswith(title.casefold())]
    return max(matches, key=len) if matches else ''


def detect_book(filename, title=''):
    stem = _strip_edition_tags(Path(filename).stem.strip())
    explicit_title = (title or '').strip()
    working = _remove_title_once(stem, explicit_title)
    number = r'(\d{1,4}(?:\.\d{1,3})?)'
    candidates = []
    for score, pattern, reason in [
        (100, rf'第\s*{number}\s*(?:卷|冊|册)', '中文卷数'),
        (98, rf'(?i)(?<![A-Z0-9])(?:VOL(?:UME)?\.?|V|EP\.?)\s*0*{number}(?!\d)', '卷数标记'),
        (92, rf'[\[(【]\s*0*{number}\s*[\])】]', '括号卷数'),
    ]:
        for match in re.finditer(pattern, working):
            candidates.append((score, _number(match[1]), reason, match.span()))

    stripped = working.strip(' ._-–—·')
    if not candidates and re.fullmatch(number, stripped):
        match = re.search(number, working)
        candidates.append((96, _number(match[1]), '纯卷数文件名', match.span()))
    if not candidates:
        for match in re.finditer(r'(?<![\d.])(\d{1,3}(?:\.\d{1,3})?)(?![\d.])', working):
            candidates.append((82, _number(match[1]), '独立数字卷数', match.span()))
    if not candidates:
        return BookDetection(series_title=explicit_title)

    best = max(x[0] for x in candidates)
    top = [x for x in candidates if x[0] == best]
    if len({x[1] for x in top}) != 1:
        return BookDetection(confidence=25, reason='多个卷数候选，请确认', series_title=explicit_title)
    score, volume, reason, span = top[0]

    inferred_title = explicit_title
    if explicit_title:
        remainder = working[:span[0]] + ' ' + working[span[1]:]
    else:
        # With no user-supplied title, the text before a high-confidence volume token is
        # the safest series-title signal. Keep the text after it as the volume subtitle.
        prefix = _trim_book_text(working[:span[0]])
        inferred_title = prefix
        remainder = working[span[1]:] if prefix else working[:span[0]] + ' ' + working[span[1]:]

    part_match = re.search(
        r'(?<![\w])(?:上册|上卷|上部|上篇|中册|中卷|中部|中篇|下册|下卷|下部|下篇|前篇|后篇|上|中|下)(?![\w])',
        remainder)
    part = _normalize_part(part_match.group(0)) if part_match else ''
    if part_match:
        remainder = remainder[:part_match.start()] + ' ' + remainder[part_match.end():]
    remainder = _trim_book_text(remainder)
    return BookDetection(volume, score, reason, remainder, part, inferred_title)


def format_book_name(template, title, volume, volume_title='', part=''):
    if volume is None:
        raise ValueError('缺少卷数')
    try:
        result = template.format(
            title=title, volume=_VolumeNumber(volume),
            volume_title=volume_title or '', part=part or '')
    except (KeyError, ValueError, AttributeError, IndexError) as exc:
        raise ValueError('模板无效，仅支持 title、volume、volume_title、part 字段') from exc
    result = re.sub(r'\s+', ' ', result).strip()
    result = re.sub(r'(?:\s*[-–—]\s*)+$', '', result).rstrip(' ._-–—')
    return core.validate_name(result)


def _signature(path):
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def _iter_books(root, recursive):
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()
                   and not getattr(Path(directory) / d, 'is_junction', lambda: False)()]
        for name in files:
            path = Path(directory) / name
            if path.suffix.lower() in BOOK_EXTS and not path.is_symlink():
                yield path
        if not recursive:
            break


def build_novel_plan(folder, title, template, recursive=False, force_sequence=False,
                     sequence_start=1, group_settings=None, overrides=None, skipped=None,
                     mode='rename', output_folder=''):
    root = Path(folder).resolve()
    if not root.is_dir():
        raise ValueError('请选择有效的输入文件夹')
    if mode not in {'rename', 'copy'}:
        raise ValueError('未知操作模式')
    if not 1 <= sequence_start <= 9999:
        raise ValueError('起始卷数须在 1–9999 之间')
    output = Path(output_folder).resolve() if output_folder else None
    if mode == 'copy' and (output is None or output == root or root in output.parents):
        raise ValueError('复制目标必须在输入文件夹之外，避免再次导入已整理文件')

    groups, overrides, skipped = group_settings or {}, overrides or {}, set(skipped or [])
    paths = sorted(_iter_books(root, recursive), key=lambda p: core.natural_key(p.relative_to(root)))
    global_title = (title or '').strip()

    # First pass: discover series names from explicit volume markers. If another file in
    # the same mixed folder has no volume marker, reuse the longest known title prefix so
    # sequence mode can still group it with the correct series.
    preliminary = {path: detect_book(path.name, global_title) for path in paths}
    if not global_title:
        known_titles = sorted({d.series_title for d in preliminary.values() if d.series_title}, key=len, reverse=True)
        for path in paths:
            if preliminary[path].series_title:
                continue
            matched = _match_known_series(path.name, known_titles)
            if matched:
                preliminary[path] = detect_book(path.name, matched)

    def base_series(path):
        return global_title or preliminary[path].series_title

    def group_for(path):
        relative = path.parent.relative_to(root).as_posix()
        series = base_series(path)
        token = re.sub(r'\s+', ' ', series).strip().casefold() if series else '__unknown__'
        return f'{relative}|BOOK|{token}', relative, series

    def group_options(key, relative):
        # Accept the short-lived v1 light-novel group id so in-session settings survive
        # an upgrade to automatic per-series grouping.
        return groups.get(key, groups.get(f'{relative}|BOOK', GroupSettings()))

    detections, item_titles, group_meta, counters = {}, {}, {}, {}
    for path in paths:
        key, relative, inferred_title = group_for(path)
        options = group_options(key, relative)
        item_title = options.title.strip() or inferred_title
        detection = detect_book(path.name, item_title) if item_title else preliminary[path]
        if item_title and not detection.series_title:
            detection.series_title = item_title
        if str(path) in overrides:
            detection.volume = parse_book_override(overrides[str(path)])
            detection.confidence = 100
            detection.reason = '手动纠正卷数'
        if force_sequence and str(path) not in overrides and str(path) not in skipped:
            volume = counters.get(key, options.start if options.start is not None else sequence_start)
            if not 1 <= volume <= 9999:
                raise ValueError('组内卷数超出 1–9999 范围')
            detection.volume = volume
            detection.confidence = 100
            detection.reason = '组内排序编号'
            counters[key] = volume + 1
        detections[path] = detection
        item_titles[path] = item_title
        group_meta[path] = (key, relative)

    plan = []
    for path in paths:
        key, relative = group_meta[path]
        item_title = item_titles[path]
        detection = detections[path]
        status = READY
        if str(path) in skipped:
            status = '已跳过'
        elif detection.volume is None:
            status = '待确认：' + detection.reason
        elif detection.confidence < 70:
            status = '待确认：低置信度'
        elif not item_title:
            status = '待填写名称'

        target = path
        if status == READY:
            try:
                base = format_book_name(template, item_title, detection.volume,
                                        detection.volume_title, detection.part)
                name = core.validate_name(base + path.suffix.lower())
                target = (output / path.parent.relative_to(root) / name) if mode == 'copy' else path.with_name(name)
                if target == path and target.name == path.name:
                    status = '无需修改'
            except ValueError as exc:
                status = '错误：' + str(exc)

        display = []
        if detection.volume is not None:
            display.append(f'V{_VolumeNumber(detection.volume):02d}')
        if detection.part:
            display.append(detection.part)
        if detection.volume_title:
            display.append(detection.volume_title)
        base_label = '当前目录' if relative == '.' else relative
        label = item_title if relative == '.' and item_title else (
            f'{base_label} / {item_title}' if item_title else base_label)
        plan.append(BookRenameItem(
            str(path), str(target), '轻小说', ' · '.join(display) if display else '—',
            detection.confidence, status, group=label, group_id=key,
            reason=detection.reason, signature=_signature(path), mode=mode,
            volume=detection.volume, volume_title=detection.volume_title, part=detection.part,
            series_title=item_title))

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


class NovelGroupDialog(tk.Toplevel):
    def __init__(self, parent, label, settings):
        super().__init__(parent)
        self.result = None
        self.title('轻小说分组：' + label)
        self.transient(parent)
        self.grab_set()
        self.configure(bg=parent.COLORS['panel'])
        body = ttk.Frame(self, style='Panel.TFrame', padding=16)
        body.pack(fill='both', expand=True)
        ttk.Label(body, text='LIGHT NOVEL GROUP / 分组规则', style='Section.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))
        self.title_entry = ttk.Entry(body, width=32)
        self.start_entry = ttk.Entry(body, width=32)
        self.title_entry.insert(0, settings.title or '')
        self.start_entry.insert(0, '' if settings.start is None else str(settings.start))
        ttk.Label(body, text='作品名称', style='MutedPanel.TLabel').grid(row=1, column=0, sticky='w', padx=(0, 10), pady=6)
        self.title_entry.grid(row=1, column=1, sticky='ew', pady=6)
        ttk.Label(body, text='排序起始卷', style='MutedPanel.TLabel').grid(row=2, column=0, sticky='w', padx=(0, 10), pady=6)
        self.start_entry.grid(row=2, column=1, sticky='ew', pady=6)
        actions = ttk.Frame(body, style='Panel.TFrame')
        actions.grid(row=3, column=0, columnspan=2, sticky='e', pady=(12, 0))
        ttk.Button(actions, text='取消', command=self.destroy, style='Ghost.TButton').pack(side='right', padx=(8, 0))
        ttk.Button(actions, text='保存设置', command=self._save, style='Primary.TButton').pack(side='right')
        body.columnconfigure(1, weight=1)
        self.bind('<Escape>', lambda _e: self.destroy())
        self.bind('<Return>', lambda _e: self._save())
        self.title_entry.focus_set()

    def _save(self):
        start = self.start_entry.get().strip()
        try:
            start = int(start) if start else None
            if start is not None and not 1 <= start <= 9999:
                raise ValueError
        except ValueError:
            self.bell()
            return
        self.result = GroupSettings(self.title_entry.get().strip(), None, start)
        self.destroy()


class LightNovelMixin:
    """Add a content switch without mixing book volume parsing into anime episode parsing."""

    def _build_ui(self):
        super()._build_ui()
        self.content_type_var = tk.StringVar(value='番剧')
        toolbar = self.run_btn.master
        ttk.Label(toolbar, text='内容', style='Cyan.TLabel').pack(side='left', padx=(10, 4))
        self.content_type_combo = ttk.Combobox(
            toolbar, values=['番剧', '轻小说'], textvariable=self.content_type_var,
            state='readonly', width=7)
        self.content_type_combo.pack(side='left', padx=(0, 6))
        self.content_type_combo.bind('<<ComboboxSelected>>', self.on_content_type_change)
        self._template_combo = self._find_template_combo()
        self.content_type_var.trace_add('write', self._novel_mode_dirty)

    def _find_template_combo(self):
        wanted = str(self.template_name_var)
        stack = list(self.winfo_children())
        while stack:
            widget = stack.pop()
            if isinstance(widget, ttk.Combobox) and str(widget.cget('textvariable')) == wanted:
                return widget
            stack.extend(widget.winfo_children())
        return None

    def _novel_mode_dirty(self, *_):
        self.groups.clear()
        self.overrides.clear()
        self.skipped.clear()
        self.dirty = True
        self.run_btn.state(['disabled'])
        self._set_chrome_state('NEEDS REFRESH', 'dirty')

    def on_content_type_change(self, _event=None):
        novel = self.content_type_var.get() == '轻小说'
        templates = NOVEL_TEMPLATES if novel else core_templates()
        if self._template_combo is not None:
            self._template_combo.configure(values=list(templates))
        name = next(iter(templates))
        self.template_name_var.set(name)
        self.template_var.set(templates[name])
        self.status_var.set('轻小说模式：支持 EPUB / MOBI / AZW3 / PDF / TXT / CBZ。' if novel
                            else '已切换回番剧模式。')
        self.detail_var.set('双击可纠正卷数；卷标题与上/下册会自动保留。' if novel
                            else '待确认的文件不会执行；悬停查看识别依据，双击可纠正集数。')

    def on_template_change(self, _event=None):
        if hasattr(self, 'content_type_var') and self.content_type_var.get() == '轻小说':
            name = self.template_name_var.get()
            if name != '自定义' and name in NOVEL_TEMPLATES:
                self.template_var.set(NOVEL_TEMPLATES[name])
            self._update_conditional_rows()
            return
        return super().on_template_change(_event)

    def scan(self):
        if not hasattr(self, 'content_type_var') or self.content_type_var.get() != '轻小说':
            return super().scan()
        if self.busy:
            return
        self.plan = []
        self.tree.delete(*self.tree.get_children())
        self.dirty = True
        self.update_run_state()
        try:
            args = dict(
                folder=self.folder_var.get().strip(), title=self.title_var.get().strip(),
                template=self.template_var.get().strip(), recursive=self.recursive_var.get(),
                force_sequence=self.force_var.get(), sequence_start=int(self.start_var.get()),
                group_settings=dict(self.groups), overrides=dict(self.overrides), skipped=set(self.skipped),
                mode='rename' if self.mode_var.get() == '原地重命名' else 'copy',
                output_folder=self.output_var.get().strip())
            if not args['folder']:
                raise ValueError('请选择输入文件夹')
        except ValueError as exc:
            self._alert('设置有误', str(exc), kind='error')
            return
        self.status_var.set('正在识别轻小说文件…')
        self._set_empty_state('正在读取书库…', '正在分析卷数、卷标题和上下册，请稍候。', visible=True)
        self._start_task(lambda _: build_novel_plan(**args), self.render_plan)

    def edit_item(self):
        if not hasattr(self, 'content_type_var') or self.content_type_var.get() != '轻小说':
            return super().edit_item()
        if not self.can_edit():
            return
        indices = self.selected_indices()
        if len(indices) != 1:
            self._alert('选择一个文件', '每次纠正一个轻小说文件。', kind='warning')
            return
        item = self.plan[indices[0]]
        initial = self.overrides.get(item.old_path, '' if item.volume is None else str(item.volume))
        value = self._prompt('纠正卷数',
            f'{Path(item.old_path).name}\n输入 03、V03、Vol.03、Ep.03 或 第3卷：', initial=initial)
        if value is None:
            return
        try:
            parse_book_override(value)
        except ValueError as exc:
            self._alert('输入有误', str(exc), kind='error')
            return
        self.overrides[item.old_path] = value
        self.scan()

    def edit_group(self):
        if not self.can_edit():
            return
        item = self.plan[self.selected_indices()[0]]
        if not hasattr(self, 'content_type_var') or self.content_type_var.get() != '轻小说':
            # Keep the original test/extension seam: GroupDialog lives in this method's globals.
            dialog = GroupDialog(self, item.group, self.groups.get(item.group_id, GroupSettings()))
            if dialog.result is not None:
                self.groups[item.group_id] = dialog.result
                self.scan()
            return
        dialog = NovelGroupDialog(self, item.group, self.groups.get(item.group_id, GroupSettings()))
        self.wait_window(dialog)
        if dialog.result is not None:
            self.groups[item.group_id] = dialog.result
            self.scan()


def core_templates():
    # Late import avoids a dependency cycle with the main UI modules.
    from ui_constants import TEMPLATES
    return TEMPLATES
