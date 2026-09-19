# -*- coding: utf-8 -*-
from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from renamer_core import (VERSION, READY, GroupSettings, build_plan, parse_override,
                          execute_plan, undo_last, recover_pending, pending_operation)

TEMPLATES = {
    '番剧名 - 01': '{title} - {episode:02d}',
    '番剧名 01': '{title} {episode:02d}',
    '番剧名 S01E01': '{title} S{season:02d}E{episode:02d}',
    '番剧名 - E01': '{title} - E{episode:02d}',
    '[01] 番剧名': '[{episode:02d}] {title}',
    '自定义': '{title} - {episode:02d}',
}


class GroupDialog(simpledialog.Dialog):
    def __init__(self, parent, label, settings):
        self.settings = settings
        super().__init__(parent, '设置分组：' + label)

    def body(self, master):
        ttk.Label(master, text='留空则使用上方的默认设置。').grid(row=0, columnspan=2, pady=8)
        self.fields = []
        for row, (label, value) in enumerate([
            ('作品名称', self.settings.title), ('季度（0–99）', self.settings.season),
            ('排序起始集（1–9999）', self.settings.start)], 1):
            ttk.Label(master, text=label).grid(row=row, column=0, sticky='w', padx=8, pady=5)
            entry = ttk.Entry(master, width=32)
            entry.insert(0, '' if value is None else str(value))
            entry.grid(row=row, column=1, padx=8, pady=5)
            self.fields.append(entry)
        return self.fields[0]

    def validate(self):
        title, season, start = [x.get().strip() for x in self.fields]
        try:
            season = int(season) if season else None
            start = int(start) if start else None
            if season is not None and not 0 <= season <= 99:
                raise ValueError('季度须在 0–99 之间')
            if start is not None and not 1 <= start <= 9999:
                raise ValueError('起始集数须在 1–9999 之间')
        except ValueError as exc:
            messagebox.showerror('输入有误', str(exc), parent=self)
            return False
        self.result = GroupSettings(title, season, start)
        return True


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'AnimeRenamer {VERSION} · 未来日记主题')
        self.geometry('1380x860')
        self.minsize(1120, 720)
        self.plan = []
        self.overrides, self.groups, self.skipped = {}, {}, set()
        self.busy, self.dirty = False, True
        self.source_context = ''
        self.group_nodes = {}
        self._build_ui()
        try:
            icon = self._load_photo('app_icon.png')
            if icon:
                self.iconphoto(True, icon)
        except tk.TclError:
            pass
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(150, self.check_recovery)

    def _pick_font(self, *preferred):
        """Return the first installed font family, with a safe Tk fallback."""
        try:
            installed = {name.casefold(): name for name in tkfont.families(self)}
        except tk.TclError:
            installed = {}
        for name in preferred:
            hit = installed.get(name.casefold())
            if hit:
                return hit
        return 'TkDefaultFont'

    def _asset_path(self, name):
        """Find ASCII-named theme assets next to source/EXE or in PyInstaller temp data."""
        roots = []
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            roots.append(Path(meipass))
        try:
            roots.append(Path(__file__).resolve().parent)
        except NameError:
            pass
        if getattr(sys, 'frozen', False):
            roots.append(Path(sys.executable).resolve().parent)
        for root in roots:
            path = root / 'assets' / name
            if path.is_file():
                return path
        return None

    def _load_photo(self, name):
        path = self._asset_path(name)
        if not path:
            return None
        try:
            photo = tk.PhotoImage(file=str(path))
            self._theme_images.append(photo)
            return photo
        except tk.TclError:
            return None

    def _draw_banner(self, _event=None):
        canvas = getattr(self, 'banner_canvas', None)
        if not canvas:
            return
        canvas.delete('overlay')
        width = max(canvas.winfo_width(), 720)
        if getattr(self, 'banner_photo', None):
            canvas.create_image(0, 0, image=self.banner_photo, anchor='nw', tags='overlay')
        # Dark veil on the right keeps text readable without altering the asset.
        canvas.create_rectangle(max(420, int(width * 0.48)), 0, width, 132,
                                fill='#0D0910', stipple='gray50', outline='', tags='overlay')
        tx = max(535, int(width * 0.61))
        canvas.create_text(tx, 32, text='ANIME RENAMER', anchor='w', fill='#FFF2F7',
                           font=(self.FONTS['display'], 21, 'bold'), tags='overlay')
        canvas.create_text(tx, 65, text='未来日记 · RENAME TERMINAL', anchor='w', fill='#FF6EA3',
                           font=(self.FONTS['body'], 10, 'bold'), tags='overlay')
        canvas.create_text(tx, 93, text='扫描  /  校对  /  预览  /  改写未来', anchor='w', fill='#C9BCC5',
                           font=(self.FONTS['body'], 9), tags='overlay')
        canvas.create_line(tx, 111, min(width - 28, tx + 330), 111,
                           fill='#6E294A', width=1, tags='overlay')

    def _build_ui(self):
        # Future Diary inspired theme: dark diary surface + pink danger accent + cyan status accent.
        # UI-only layer; rename/copy/undo logic remains unchanged.
        self.COLORS = {
            'bg': '#0D0B11',
            'panel': '#141119',
            'panel2': '#1B1620',
            'panel3': '#231A25',
            'border': '#3A2835',
            'text': '#F6EEF4',
            'muted': '#A89BA6',
            'pink': '#FF4F91',
            'pink2': '#D82D72',
            'red': '#C62E45',
            'cyan': '#38D6D0',
            'violet': '#8C79D8',
            'warning': '#F0A14A',
            'error': '#FF5F6D',
            'success': '#42E3C4',
        }
        c = self.COLORS
        self.configure(bg=c['bg'])
        self._theme_images = []
        self.FONTS = {
            'body': self._pick_font('Microsoft YaHei UI', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans SC', 'PingFang SC', 'Segoe UI'),
            'display': self._pick_font('Segoe UI Variable Display', 'Microsoft YaHei UI', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Segoe UI'),
            'jp': self._pick_font('Yu Gothic UI', 'Yu Gothic', 'Meiryo UI', 'Noto Sans CJK JP', 'Noto Sans JP', 'Microsoft YaHei UI'),
            'mono': self._pick_font('Cascadia Mono', 'JetBrains Mono', 'Consolas', 'DejaVu Sans Mono'),
        }
        self.option_add('*Font', (self.FONTS['body'], 10))

        style = ttk.Style(self)
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        # Base controls
        style.configure('.',
                        background=c['bg'], foreground=c['text'],
                        fieldbackground=c['panel2'], bordercolor=c['border'],
                        lightcolor=c['border'], darkcolor=c['border'],
                        font=(self.FONTS['body'], 10))
        style.configure('App.TFrame', background=c['bg'])
        style.configure('Panel.TFrame', background=c['panel'])
        style.configure('Card.TFrame', background=c['panel2'])
        style.configure('Sidebar.TFrame', background='#110C14')
        style.configure('TLabel', background=c['bg'], foreground=c['text'])
        style.configure('Panel.TLabel', background=c['panel'], foreground=c['text'])
        style.configure('Card.TLabel', background=c['panel2'], foreground=c['text'])
        style.configure('Muted.TLabel', background=c['bg'], foreground=c['muted'])
        style.configure('MutedPanel.TLabel', background=c['panel'], foreground=c['muted'])
        style.configure('Sidebar.TLabel', background='#110C14', foreground=c['text'])
        style.configure('SidebarMuted.TLabel', background='#110C14', foreground='#A98E9E')
        style.configure('Hero.TLabel', background='#110C14', foreground='#FFF1F7',
                        font=(self.FONTS['display'], 20, 'bold'))
        style.configure('HeroSub.TLabel', background='#110C14', foreground=c['pink'],
                        font=(self.FONTS['mono'], 8, 'bold'))
        style.configure('Title.TLabel', background=c['bg'], foreground=c['text'],
                        font=(self.FONTS['display'], 18, 'bold'))
        style.configure('Section.TLabel', background=c['panel'], foreground=c['text'],
                        font=(self.FONTS['body'], 11, 'bold'))
        style.configure('Accent.TLabel', background=c['panel'], foreground=c['pink'])
        style.configure('Cyan.TLabel', background=c['panel2'], foreground=c['cyan'],
                        font=(self.FONTS['mono'], 8, 'bold'))

        style.configure('TEntry', padding=7, relief='flat', borderwidth=1,
                        foreground=c['text'], fieldbackground=c['panel3'])
        style.map('TEntry', fieldbackground=[('disabled', '#17131A')],
                  foreground=[('disabled', '#706670')])
        style.configure('TCombobox', padding=6, arrowsize=14,
                        foreground=c['text'], fieldbackground=c['panel3'])
        style.map('TCombobox', fieldbackground=[('readonly', c['panel3'])],
                  selectbackground=[('readonly', c['panel3'])],
                  selectforeground=[('readonly', c['text'])])
        style.configure('TSpinbox', padding=6, arrowsize=12,
                        foreground=c['text'], fieldbackground=c['panel3'])
        style.configure('TCheckbutton', background=c['panel'], foreground=c['text'], padding=2)
        style.map('TCheckbutton', background=[('active', c['panel'])],
                  foreground=[('active', c['text'])],
                  indicatorcolor=[('selected', c['pink']), ('!selected', '#5D505A')])

        style.configure('TButton', padding=(12, 8), relief='flat', borderwidth=1,
                        background=c['panel3'], foreground=c['text'])
        style.map('TButton', background=[('active', '#332536'), ('pressed', '#241A28'), ('disabled', '#17141A')],
                  foreground=[('disabled', '#655C65')])
        style.configure('Primary.TButton', padding=(16, 9), background=c['pink2'],
                        foreground='#FFFFFF', bordercolor=c['pink'])
        style.map('Primary.TButton', background=[('active', c['pink']), ('pressed', '#B61F5C'), ('disabled', '#442537')],
                  foreground=[('disabled', '#957A88')])
        style.configure('Danger.TButton', background='#3A1820', foreground='#FF8B99', bordercolor='#702535')
        style.map('Danger.TButton', background=[('active', '#52202B')])
        style.configure('Ghost.TButton', background=c['panel2'], foreground=c['muted'], bordercolor=c['border'])
        style.map('Ghost.TButton', background=[('active', c['panel3'])], foreground=[('active', c['text'])])
        style.configure('Cyan.TButton', background='#143638', foreground='#74FFF3', bordercolor='#246B6A')
        style.map('Cyan.TButton', background=[('active', '#1B4A4A')])

        style.configure('Treeview', rowheight=32, relief='flat', borderwidth=0,
                        background='#121017', fieldbackground='#121017', foreground='#EDE5EC',
                        font=(self.FONTS['body'], 9))
        style.configure('Treeview.Heading', background='#211923', foreground='#EADCE7',
                        relief='flat', borderwidth=0, padding=(8, 8), font=(self.FONTS['body'], 9, 'bold'))
        style.map('Treeview', background=[('selected', '#4A1F39')], foreground=[('selected', '#FFFFFF')])
        style.map('Treeview.Heading', background=[('active', '#312336')])
        style.configure('Vertical.TScrollbar', background='#251B28', troughcolor='#121017', arrowcolor='#998793')
        style.configure('Horizontal.TScrollbar', background='#251B28', troughcolor='#121017', arrowcolor='#998793')

        # Main composition: image-backed themed sidebar + working area.
        shell = ttk.Frame(self, style='App.TFrame')
        shell.pack(fill='both', expand=True)
        sidebar = ttk.Frame(shell, style='Sidebar.TFrame', width=280)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        main = ttk.Frame(shell, style='App.TFrame', padding=(18, 14, 18, 14))
        main.pack(side='left', fill='both', expand=True)

        # Sidebar uses an optimized local PNG generated for this theme.
        self.sidebar_photo = self._load_photo('yuno_sidebar.png')
        if self.sidebar_photo:
            tk.Label(sidebar, image=self.sidebar_photo, bg='#110C14', bd=0,
                     highlightthickness=0).pack(fill='x')
        else:
            fallback = tk.Canvas(sidebar, width=280, height=390, bg='#110C14', highlightthickness=0)
            fallback.pack(fill='x')
            fallback.create_oval(45, 42, 235, 230, fill='#321326', outline='#74244D', width=2)
            fallback.create_text(140, 182, text='MIRAI NIKKI', fill='#FF6EA3',
                                 font=(self.FONTS['display'], 16, 'bold'))
            fallback.create_text(140, 214, text='theme asset missing', fill='#927B8A',
                                 font=(self.FONTS['mono'], 8))

        side_text = ttk.Frame(sidebar, style='Sidebar.TFrame', padding=(20, 9, 18, 16))
        side_text.pack(fill='both', expand=True)
        ttk.Label(side_text, text='未来日记', style='Hero.TLabel').pack(anchor='w')
        ttk.Label(side_text, text='MIRAI NIKKI  /  RENAME TERMINAL', style='HeroSub.TLabel').pack(anchor='w', pady=(2, 12))
        ttk.Label(side_text, text='未来は、まだ書き換えられる。', style='Sidebar.TLabel',
                  font=(self.FONTS['jp'], 10, 'bold')).pack(anchor='w')
        ttk.Label(side_text, text='文件名的未来，由你确认后再改写。', style='SidebarMuted.TLabel',
                  font=(self.FONTS['body'], 9), justify='left').pack(anchor='w', pady=(5, 13))
        ttk.Separator(side_text, orient='horizontal').pack(fill='x', pady=(2, 10))
        ttk.Label(side_text, text='●  PINK   改写 / 主操作', style='SidebarMuted.TLabel').pack(anchor='w', pady=2)
        ttk.Label(side_text, text='●  CYAN   安全 / 可执行', style='SidebarMuted.TLabel').pack(anchor='w', pady=2)
        ttk.Label(side_text, text='●  RED    冲突 / 风险', style='SidebarMuted.TLabel').pack(anchor='w', pady=2)
        ttk.Label(side_text, text=f'AnimeRenamer {VERSION}', style='SidebarMuted.TLabel',
                  font=(self.FONTS['mono'], 8)).pack(side='bottom', anchor='w')

        # Image-backed top banner. Text is rendered by Tk to keep Chinese/Japanese crisp.
        self.banner_photo = self._load_photo('yuno_banner.png')
        self.banner_canvas = tk.Canvas(main, height=132, bg='#140C13', bd=0,
                                       highlightthickness=0, relief='flat')
        self.banner_canvas.pack(fill='x', pady=(0, 11))
        self.banner_canvas.bind('<Configure>', self._draw_banner)
        self.after_idle(self._draw_banner)

        # Form card
        form_card = ttk.Frame(main, style='Panel.TFrame', padding=(14, 12))
        form_card.pack(fill='x')
        ttk.Label(form_card, text='01  日记源 / FILE SOURCE', style='Section.TLabel').grid(row=0, column=0, columnspan=7, sticky='w', pady=(0, 8))
        self.folder_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.season_var = tk.StringVar(value='1')
        self.template_name_var = tk.StringVar(value='番剧名 - 01')
        self.template_var = tk.StringVar(value=TEMPLATES['番剧名 - 01'])
        self.mode_var = tk.StringVar(value='原地重命名')
        self.output_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar()
        self.sub_var = tk.BooleanVar(value=True)
        self.lang_var = tk.BooleanVar(value=True)
        self.force_var = tk.BooleanVar()
        self.start_var = tk.StringVar(value='1')

        def field_label(text, row, col):
            ttk.Label(form_card, text=text, style='MutedPanel.TLabel').grid(row=row, column=col, sticky='w', padx=(0, 8), pady=5)

        field_label('输入文件夹', 1, 0)
        ttk.Entry(form_card, textvariable=self.folder_var).grid(row=1, column=1, columnspan=5, sticky='ew', pady=5)
        ttk.Button(form_card, text='浏览', command=self.choose_folder, style='Ghost.TButton').grid(row=1, column=6, padx=(8, 0))

        field_label('作品名称', 2, 0)
        ttk.Entry(form_card, textvariable=self.title_var, width=26).grid(row=2, column=1, sticky='ew', pady=5)
        field_label('季度', 2, 2)
        ttk.Spinbox(form_card, from_=0, to=99, width=5, textvariable=self.season_var).grid(row=2, column=3, sticky='ew')
        field_label('命名规则', 2, 4)
        cb = ttk.Combobox(form_card, values=list(TEMPLATES), textvariable=self.template_name_var, state='readonly')
        cb.grid(row=2, column=5, sticky='ew')
        cb.bind('<<ComboboxSelected>>', self.on_template_change)
        ttk.Button(form_card, text='扫描文件', command=self.scan, style='Primary.TButton').grid(row=2, column=6, padx=(8, 0))

        field_label('模板', 3, 0)
        self.template_entry = ttk.Entry(form_card, textvariable=self.template_var, state='disabled')
        self.template_entry.grid(row=3, column=1, columnspan=5, sticky='ew', pady=5)
        ttk.Label(form_card, text='支持 {title} / {season} / {episode}', style='MutedPanel.TLabel').grid(row=3, column=6, sticky='w', padx=(8, 0))

        field_label('操作方式', 4, 0)
        ttk.Combobox(form_card, textvariable=self.mode_var, state='readonly',
                     values=['原地重命名', '复制整理（保留原文件）']).grid(row=4, column=1, sticky='ew', pady=5)
        field_label('复制到', 4, 2)
        self.output_entry = ttk.Entry(form_card, textvariable=self.output_var)
        self.output_entry.grid(row=4, column=3, columnspan=3, sticky='ew')
        ttk.Button(form_card, text='选择', command=self.choose_output, style='Ghost.TButton').grid(row=4, column=6, padx=(8, 0))

        opts = ttk.Frame(form_card, style='Panel.TFrame')
        opts.grid(row=5, column=0, columnspan=7, sticky='w', pady=(10, 2))
        for text, variable in [('包含子文件夹', self.recursive_var), ('联动字幕', self.sub_var),
                               ('保留字幕语言', self.lang_var), ('每组全部正片按排序编号', self.force_var)]:
            ttk.Checkbutton(opts, text=text, variable=variable).pack(side='left', padx=(0, 14))
        ttk.Label(opts, text='起始集', style='MutedPanel.TLabel').pack(side='left')
        ttk.Spinbox(opts, from_=1, to=9999, textvariable=self.start_var, width=6).pack(side='left', padx=6)
        form_card.columnconfigure(1, weight=2)
        form_card.columnconfigure(5, weight=2)

        # Action strip
        toolbar = ttk.Frame(main, style='App.TFrame')
        toolbar.pack(fill='x', pady=(10, 8))
        ttk.Button(toolbar, text='设置所选分组', command=self.edit_group).pack(side='left', padx=(0, 7))
        ttk.Button(toolbar, text='纠正集数 / 特别篇', command=self.edit_item).pack(side='left', padx=(0, 7))
        ttk.Button(toolbar, text='跳过 / 恢复', command=self.toggle_skip).pack(side='left', padx=(0, 7))
        ttk.Button(toolbar, text='清除纠正', command=self.clear_override, style='Ghost.TButton').pack(side='left', padx=(0, 7))
        ttk.Label(toolbar, text='双击文件纠正 · 空格切换跳过', style='Muted.TLabel').pack(side='right')

        # Preview card
        preview_card = ttk.Frame(main, style='Panel.TFrame', padding=(10, 10))
        preview_card.pack(fill='both', expand=True)
        preview_head = ttk.Frame(preview_card, style='Panel.TFrame')
        preview_head.pack(fill='x', pady=(0, 7))
        ttk.Label(preview_head, text='02  未来记录 / RENAME PREVIEW', style='Section.TLabel').pack(side='left')
        ttk.Label(preview_head, text='绿色 = 可执行    橙色 = 待确认    红色 = 冲突', style='MutedPanel.TLabel').pack(side='right')

        preview = ttk.Frame(preview_card, style='Panel.TFrame')
        preview.pack(fill='both', expand=True)
        cols = ('kind', 'old', 'detected', 'new', 'status')
        self.tree = ttk.Treeview(preview, columns=cols, show='tree headings', selectmode='extended')
        self.tree.heading('#0', text='分组 / GROUP')
        self.tree.column('#0', width=170, minwidth=110)
        for col, label, width in [('kind', '类型', 55), ('old', '原文件名', 255),
                                  ('detected', '识别结果', 105), ('new', '目标文件名', 255),
                                  ('status', '状态', 200)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, minwidth=55)
        self.tree.tag_configure('ready', foreground='#7CF6D9')
        self.tree.tag_configure('warning', foreground=c['warning'])
        self.tree.tag_configure('error', foreground=c['error'])
        self.tree.tag_configure('skipped', foreground='#746B73')
        ybar = ttk.Scrollbar(preview, orient='vertical', command=self.tree.yview)
        xbar = ttk.Scrollbar(preview, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        ybar.grid(row=0, column=1, sticky='ns')
        xbar.grid(row=1, column=0, sticky='ew')
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(0, weight=1)
        self.tree.bind('<Double-1>', lambda e: self.edit_item())
        self.tree.bind('<space>', lambda e: self.toggle_skip())
        self.tree.bind('<<TreeviewSelect>>', self.show_detail)

        # Detail/status bar
        detail_card = ttk.Frame(main, style='Card.TFrame', padding=(11, 8))
        detail_card.pack(fill='x', pady=(8, 0))
        self.detail_var = tk.StringVar(value='待确认的文件不会执行。若识别不正确，请双击对应文件进行纠正。')
        ttk.Label(detail_card, text='DIARY LOG', style='Cyan.TLabel').pack(anchor='w')
        ttk.Label(detail_card, textvariable=self.detail_var, style='Card.TLabel', wraplength=1000).pack(fill='x', pady=(2, 0))

        footer = ttk.Frame(main, style='App.TFrame')
        footer.pack(fill='x', pady=(9, 0))
        left_footer = ttk.Frame(footer, style='App.TFrame')
        left_footer.pack(side='left', fill='x', expand=True)
        self.status_var = tk.StringVar(value='选择文件夹，填写作品名，然后扫描未来记录。')
        ttk.Label(left_footer, textvariable=self.status_var, style='Muted.TLabel', wraplength=700).pack(anchor='w')
        ttk.Button(footer, text='恢复中断操作', command=self.recover, style='Ghost.TButton').pack(side='left', padx=(8, 0))
        ttk.Button(footer, text='撤销上次操作', command=self.undo, style='Danger.TButton').pack(side='left', padx=8)
        self.run_btn = ttk.Button(footer, text='改写未来 · 执行', command=self.execute, state='disabled', style='Primary.TButton')
        self.run_btn.pack(side='right')

        for variable in [self.folder_var, self.title_var, self.season_var, self.template_var,
                         self.mode_var, self.output_var, self.recursive_var, self.sub_var,
                         self.lang_var, self.force_var, self.start_var]:
            variable.trace_add('write', self.settings_changed)

    def settings_changed(self, *_):
        if self.folder_var.get() != self.source_context:
            self.groups.clear()
            self.overrides.clear()
            self.skipped.clear()
            self.source_context = self.folder_var.get()
        self.dirty = True
        self.run_btn.state(['disabled'])
        self.status_var.set('设置已改变，请刷新预览后执行。')

    def choose_folder(self):
        folder = filedialog.askdirectory(parent=self, title='选择输入文件夹')
        if folder:
            self.folder_var.set(folder)
            self.scan()

    def choose_output(self):
        folder = filedialog.askdirectory(parent=self, title='选择复制目标文件夹')
        if folder:
            self.output_var.set(folder)

    def on_template_change(self, _event=None):
        name = self.template_name_var.get()
        if name != '自定义':
            self.template_var.set(TEMPLATES[name])
        self.template_entry.configure(state='normal' if name == '自定义' else 'disabled')

    def _controls(self, widget):
        for child in widget.winfo_children():
            if isinstance(child, (ttk.Entry, ttk.Button, ttk.Checkbutton, ttk.Combobox, ttk.Spinbox)):
                yield child
            yield from self._controls(child)

    def _start_task(self, function, completed):
        if self.busy:
            return
        self.busy = True
        states = [(w, w.state()) for w in self._controls(self)]
        for widget, _ in states:
            widget.state(['disabled'])
        events = queue.Queue()

        def worker():
            try:
                events.put(('done', function(lambda *p: events.put(('progress', p)))))
            except Exception as exc:
                events.put(('error', str(exc)))

        def poll():
            try:
                while True:
                    kind, result = events.get_nowait()
                    if kind == 'progress':
                        self.status_var.set(f'处理中 {result[0]}/{result[1]}：{result[2]}')
                        continue
                    self.busy = False
                    for widget, state in states:
                        widget.state(['!disabled'])
                        widget.state(state)
                    if kind == 'error':
                        self.dirty = True
                        messagebox.showerror('操作失败', result, parent=self)
                    else:
                        completed(result)
                    self.update_run_state()
                    return
            except queue.Empty:
                self.after(60, poll)
        threading.Thread(target=worker, daemon=False).start()
        self.after(60, poll)

    def scan(self):
        if self.busy:
            return
        self.plan = []
        self.tree.delete(*self.tree.get_children())
        self.dirty = True
        self.update_run_state()
        try:
            args = dict(folder=self.folder_var.get().strip(), title=self.title_var.get().strip(),
                        season=int(self.season_var.get()), template=self.template_var.get().strip(),
                        recursive=self.recursive_var.get(), rename_subtitles=self.sub_var.get(),
                        preserve_language=self.lang_var.get(), force_sequence=self.force_var.get(),
                        sequence_start=int(self.start_var.get()), group_settings=dict(self.groups),
                        overrides=dict(self.overrides), skipped=set(self.skipped),
                        mode='rename' if self.mode_var.get() == '原地重命名' else 'copy',
                        output_folder=self.output_var.get().strip())
            if not args['folder']:
                raise ValueError('请选择输入文件夹')
        except ValueError as exc:
            messagebox.showerror('设置有误', str(exc), parent=self)
            return
        self.status_var.set('正在识别文件…')
        self._start_task(lambda _: build_plan(**args), self.render_plan)

    def render_plan(self, plan):
        self.plan, self.dirty, self.group_nodes = plan, False, {}
        nodes = {}
        for index, item in enumerate(plan):
            if item.group_id not in nodes:
                node = f'g{len(nodes)}'
                nodes[item.group_id] = node
                self.group_nodes[node] = item.group_id
                options = self.groups.get(item.group_id, GroupSettings())
                label = item.group + (' → ' + options.title if options.title else '')
                self.tree.insert('', 'end', iid=node, text=label, open=True)
            status = item.status
            tag = 'error' if status.startswith(('冲突', '错误')) else ('warning' if status.startswith(('待',)) else ('skipped' if status == '已跳过' else ('ready' if status == READY else '')))
            self.tree.insert(nodes[item.group_id], 'end', iid=f'r{index}', values=(
                item.kind, Path(item.old_path).name, item.detected,
                Path(item.new_path).name if item.new_path != item.old_path else '—', status), tags=(tag,))
        ready = sum(x.status == READY for x in plan)
        review = sum(x.status.startswith('待') for x in plan)
        self.status_var.set(f'{len(nodes)} 组 · {len(plan)} 个文件 · 可执行 {ready} · 待确认/填写 {review} · 已跳过 {sum(x.status == "已跳过" for x in plan)}')

    def update_run_state(self):
        allowed = not self.busy and not self.dirty and any(x.status == READY for x in self.plan)
        allowed = allowed and not any(x.status.startswith(('冲突', '错误')) for x in self.plan)
        self.run_btn.state(['!disabled'] if allowed else ['disabled'])

    def selected_indices(self):
        indices = set()
        for node in self.tree.selection():
            if node.startswith('r'):
                indices.add(int(node[1:]))
            elif node in self.group_nodes:
                indices.update(int(n[1:]) for n in self.tree.get_children(node))
        return sorted(indices)

    def can_edit(self):
        if self.busy:
            return False
        if self.dirty:
            messagebox.showinfo('请刷新预览', '请先刷新预览，再编辑或跳过文件。', parent=self)
            return False
        return bool(self.selected_indices())

    def show_detail(self, _event=None):
        indices = self.selected_indices()
        if indices and indices[0] < len(self.plan):
            item = self.plan[indices[0]]
            self.detail_var.set(f'{item.reason}（规则评分 {item.confidence}/100）\n{item.old_path}\n→ {item.new_path}')

    def edit_group(self):
        if not self.can_edit():
            return
        item = self.plan[self.selected_indices()[0]]
        dialog = GroupDialog(self, item.group, self.groups.get(item.group_id, GroupSettings()))
        if dialog.result is not None:
            self.groups[item.group_id] = dialog.result
            self.scan()

    def edit_item(self):
        if not self.can_edit():
            return
        indices = self.selected_indices()
        if len(indices) != 1:
            messagebox.showinfo('选择一个文件', '每次纠正一个文件；视频纠正后，关联字幕会一起更新。', parent=self)
            return
        item = self.plan[indices[0]]
        value = simpledialog.askstring('纠正集数 / 特别篇',
            f'{Path(item.old_path).name}\n输入 03、12.5、SP01 或 NCOP02：',
            initialvalue=self.overrides.get(item.old_path, item.detected if item.detected != '—' else ''), parent=self)
        if value is not None:
            try:
                parse_override(value)
            except ValueError as exc:
                messagebox.showerror('输入有误', str(exc), parent=self)
                return
            self.overrides[item.old_path] = value
            self.scan()

    def clear_override(self):
        if self.can_edit():
            for i in self.selected_indices():
                self.overrides.pop(self.plan[i].old_path, None)
            self.scan()

    def toggle_skip(self):
        if not self.can_edit():
            return 'break'
        paths = [self.plan[i].old_path for i in self.selected_indices()]
        restore = all(p in self.skipped for p in paths)
        for path in paths:
            if restore:
                self.skipped.discard(path)
            else:
                self.skipped.add(path)
        self.scan()
        return 'break'

    def execute(self):
        if self.busy or self.dirty:
            return
        if any(x.status.startswith(('冲突', '错误')) for x in self.plan):
            messagebox.showerror('无法执行', '请先解决或跳过冲突和错误。', parent=self)
            return
        count = sum(x.status == READY for x in self.plan)
        if not count:
            return
        skipped = len(self.plan) - count
        action = '原地重命名' if self.mode_var.get() == '原地重命名' else '复制整理（保留原文件）'
        if messagebox.askyesno('确认执行', f'{action}：{count} 个文件。\n其余 {skipped} 个不执行。\n按当前预览继续？', parent=self):
            plan = list(self.plan)
            self._start_task(lambda progress: execute_plan(plan, progress), self.operation_done)

    def operation_done(self, result):
        self.dirty = True
        self.status_var.set(result['message'])
        show = messagebox.showinfo if result['ok'] else messagebox.showerror
        show('完成' if result['ok'] else '未完成', result['message'], parent=self)
        if result['ok']:
            self.overrides.clear()
            self.skipped.clear()
        self.detail_var.set('文件状态已改变，请刷新预览。')

    def undo(self):
        if not self.busy and messagebox.askyesno('撤销上次操作',
                '改名操作将恢复原名；复制操作将删除本工具上次生成的副本，保留原文件。\n文件已改变时会停止撤销。继续？', parent=self):
            self._start_task(lambda _: undo_last(), self.operation_done)

    def recover(self):
        self._start_task(lambda _: recover_pending(), self.operation_done)

    def check_recovery(self):
        try:
            if pending_operation():
                self.status_var.set('发现未完成的操作，请先点击“恢复中断操作”。')
        except OSError as exc:
            self.status_var.set(f'恢复记录目录不可用：{exc}')

    def close(self):
        if self.busy:
            messagebox.showinfo('正在处理', '请等待当前操作完成后关闭。', parent=self)
        else:
            self.destroy()

    def destroy(self):
        for callback in self.tk.splitlist(self.tk.call('after', 'info')):
            self.after_cancel(callback)
        super().destroy()


if __name__ == '__main__':
    App().mainloop()
