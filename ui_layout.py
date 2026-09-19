import queue
import tkinter as tk
from tkinter import ttk

from renamer_core import VERSION
from ui_constants import TEMPLATES
from ui_theme import ThemeToggle


class LayoutMixin:
    def _build_ui(self):
        self._configure_theme()
        c = self.COLORS
        # Main composition: image-backed themed sidebar + working area.
        shell = ttk.Frame(self, style='App.TFrame')
        shell.pack(fill='both', expand=True)
        sidebar = ttk.Frame(shell, style='Sidebar.TFrame', width=236)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        # A slim dual-tone rail separates artwork from the working surface.
        side_rail = tk.Canvas(shell, width=2, bg='#251620', bd=0, highlightthickness=0)
        side_rail.pack(side='left', fill='y')
        side_rail.create_line(0, 0, 0, 10000, fill='#7A2B52', width=1)
        side_rail.create_line(1, 0, 1, 10000, fill='#24575A', width=1)
        main = ttk.Frame(shell, style='App.TFrame', padding=(13, 9, 13, 9))
        main.pack(side='left', fill='both', expand=True)

        # Sidebar artwork is pre-rendered at its exact display size from a high-resolution
        # source, with a safe top margin so the character's hair/head is never cropped.
        art_slot = tk.Frame(sidebar, bg='#110C14', width=236, height=336, bd=0, highlightthickness=0)
        art_slot.pack(fill='x')
        art_slot.pack_propagate(False)
        self.sidebar_photo = self._load_photo('yuno_sidebar.png')
        if self.sidebar_photo:
            tk.Label(art_slot, image=self.sidebar_photo, bg='#110C14', bd=0,
                     highlightthickness=0).pack(fill='x', pady=(6, 0))
        else:
            fallback = tk.Canvas(art_slot, width=236, height=328, bg='#110C14', highlightthickness=0)
            fallback.pack(fill='x', pady=(6, 0))
            fallback.create_oval(32, 34, 204, 206, fill='#321326', outline='#74244D', width=2)
            fallback.create_text(118, 164, text='MIRAI NIKKI', fill='#FF6EA3',
                                 font=(self.FONTS['display'], 16, 'bold'))
            fallback.create_text(118, 194, text='theme asset missing', fill='#927B8A',
                                 font=(self.FONTS['mono'], 8))

        # Split sidebar copy into three visual zones.  This avoids clustering every label
        # directly below the artwork and leaving a large dead area near the bottom.
        side_text = ttk.Frame(sidebar, style='Sidebar.TFrame', padding=(17, 10, 16, 14))
        side_text.pack(fill='both', expand=True)

        side_intro = ttk.Frame(side_text, style='Sidebar.TFrame')
        side_intro.pack(fill='x')
        ttk.Label(side_intro, text='未来日记', style='Hero.TLabel').pack(anchor='w')
        ttk.Label(side_intro, text='MIRAI NIKKI  /  RENAME TERMINAL', style='HeroSub.TLabel').pack(anchor='w', pady=(2, 8))
        ttk.Label(side_intro, text='未来は、まだ書き換えられる。', style='Sidebar.TLabel',
                  font=(self.FONTS['jp'], 10, 'bold')).pack(anchor='w')
        ttk.Label(side_intro, text='确认预览，再改写文件名。', style='SidebarMuted.TLabel',
                  font=(self.FONTS['body'], 8), justify='left').pack(anchor='w', pady=(4, 0))

        ttk.Frame(side_text, style='Sidebar.TFrame').pack(fill='both', expand=True)

        side_flow = ttk.Frame(side_text, style='Sidebar.TFrame')
        side_flow.pack(fill='x', pady=(8, 0))
        ttk.Separator(side_flow, orient='horizontal').pack(fill='x', pady=(0, 8))
        ttk.Label(side_flow, text='DIARY FLOW', style='HeroSub.TLabel',
                  font=(self.FONTS['mono'], 7, 'bold')).pack(anchor='w')
        for step, action, note in [('01', 'SCAN', '读取文件'), ('02', 'CHECK', '校对未来'),
                                   ('03', 'REWRITE', '执行改名')]:
            row = ttk.Frame(side_flow, style='Sidebar.TFrame')
            row.pack(fill='x', pady=(4 if step == '01' else 2, 0))
            ttk.Label(row, text=step, style='SidebarMuted.TLabel',
                      font=(self.FONTS['mono'], 7, 'bold'), width=3).pack(side='left')
            ttk.Label(row, text=action, style='SidebarMuted.TLabel',
                      font=(self.FONTS['mono'], 7, 'bold'), width=9).pack(side='left')
            ttk.Label(row, text=note, style='SidebarMuted.TLabel',
                      font=(self.FONTS['body'], 7)).pack(side='left')

        side_bottom = ttk.Frame(side_text, style='Sidebar.TFrame')
        side_bottom.pack(fill='x', pady=(16, 0))
        ttk.Separator(side_bottom, orient='horizontal').pack(fill='x', pady=(0, 8))
        tk.Label(side_bottom, text='LOCAL / OFFLINE  ·  SAFE PREVIEW', bg='#110C14', fg='#59CFC8',
                 font=(self.FONTS['mono'], 7, 'bold'), bd=0).pack(anchor='w')
        ttk.Label(side_bottom, text=f'AnimeRenamer {VERSION}', style='SidebarMuted.TLabel',
                  font=(self.FONTS['mono'], 8)).pack(anchor='w', pady=(5, 0))

        # Compact themed chrome strip under the system title bar.
        chrome = ttk.Frame(main, style='Chrome.TFrame', padding=(11, 6))
        chrome.pack(fill='x', pady=(0, 7))
        chrome.columnconfigure(1, weight=1)
        ttk.Label(chrome, text='ANIME RENAMER', style='Cyan.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(chrome, text='未来日记 · DIARY CONTROL', style='Accent.TLabel').grid(row=0, column=1, sticky='w', padx=(10, 0))
        self.chrome_state_var = tk.StringVar(value='WAITING')
        self.chrome_state_label = tk.Label(chrome, textvariable=self.chrome_state_var, bg='#132223', fg='#74FFF3', bd=1,
                 relief='solid', padx=10, pady=4, highlightthickness=1, highlightbackground='#275A60',
                 font=(self.FONTS['mono'], 8, 'bold'))
        self.chrome_state_label.grid(row=0, column=2, sticky='e')
        self.chrome_status_line = tk.Frame(chrome, bg='#3A3239', height=2, bd=0)
        self.chrome_status_line.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(5, 0))

        # Banner art is pre-scaled to 760x82 for the compact window; text stays native Tk for crispness.
        self.banner_photo = self._load_photo('yuno_banner.png')
        self.banner_photo_wide = self._load_photo('yuno_banner_wide.png')
        self.banner_canvas = tk.Canvas(main, height=82, bg='#140C13', bd=0,
                                       highlightthickness=1, highlightbackground='#3A2835', relief='flat')
        self.banner_canvas.pack(fill='x', pady=(0, 8))
        self.banner_canvas.bind('<Configure>', self._draw_banner)
        self.after_idle(self._draw_banner)

        # Form card: subtle 1px diary-card boundary, not a generic boxed panel.
        form_outer = tk.Frame(main, bg='#3B2A36', bd=0, highlightthickness=0)
        form_outer.pack(fill='x')
        self.form_status_line = tk.Frame(form_outer, bg='#7B2C52', height=2, bd=0)
        self.form_status_line.pack(fill='x')
        form_card = ttk.Frame(form_outer, style='Panel.TFrame', padding=(11, 6))
        form_card.pack(fill='x', padx=1, pady=(0, 1))
        self._clip_card_corners(form_outer, c['bg'], 4)
        ttk.Label(form_card, text='01  日记源 / FILE SOURCE', style='Section.TLabel').grid(row=0, column=0, columnspan=7, sticky='w', pady=(0, 4))
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

        def field_label(text, row, col, icon_key):
            label = ttk.Label(form_card, text=text, image=self.UI_ICONS.get(icon_key), compound='left',
                              style='MutedPanel.TLabel')
            label.grid(row=row, column=col, sticky='w', padx=(0, 8), pady=4)
            return label

        field_label('文件夹', 1, 0, 'folder')
        ttk.Entry(form_card, textvariable=self.folder_var).grid(row=1, column=1, columnspan=5, sticky='ew', pady=4, padx=(0, 2))
        ttk.Button(form_card, text='浏览', image=self.UI_ICONS['folder'], compound='left',
                   command=self.choose_folder, style='Ghost.TButton').grid(row=1, column=6, padx=(8, 0))

        field_label('作品', 2, 0, 'title')
        ttk.Entry(form_card, textvariable=self.title_var, width=26).grid(row=2, column=1, sticky='ew', pady=4, padx=(0, 8))
        field_label('季度', 2, 2, 'season')
        ttk.Spinbox(form_card, from_=0, to=99, width=5, textvariable=self.season_var).grid(row=2, column=3, sticky='ew')
        field_label('规则', 2, 4, 'rule')
        cb = ttk.Combobox(form_card, values=list(TEMPLATES), textvariable=self.template_name_var, state='readonly')
        cb.grid(row=2, column=5, sticky='ew')
        cb.bind('<<ComboboxSelected>>', self.on_template_change)
        ttk.Button(form_card, text='扫描文件', image=self.UI_ICONS['scan'], compound='left',
                   command=self.scan, style='Primary.TButton').grid(row=2, column=6, padx=(8, 0))

        self.template_label = field_label('模板', 3, 0, 'rule')
        self.template_entry = ttk.Entry(form_card, textvariable=self.template_var, state='disabled')
        self.template_entry.grid(row=3, column=1, columnspan=5, sticky='ew', pady=4)
        self.template_hint = ttk.Label(form_card, text='{title}  /  {season}  /  {episode}', style='MutedPanel.TLabel',
                                       font=(self.FONTS['mono'], 8))
        self.template_hint.grid(row=3, column=6, sticky='w', padx=(8, 0))

        field_label('模式', 4, 0, 'mode')
        self.mode_combo = ttk.Combobox(form_card, textvariable=self.mode_var, state='readonly',
                                       values=['原地重命名', '复制整理（保留原文件）'])
        self.mode_combo.grid(row=4, column=1, sticky='ew', pady=4)
        self.output_label = field_label('复制到', 4, 2, 'target')
        self.output_entry = ttk.Entry(form_card, textvariable=self.output_var)
        self.output_entry.grid(row=4, column=3, columnspan=3, sticky='ew')
        self.output_button = ttk.Button(form_card, text='选择目录', image=self.UI_ICONS['target'], compound='left',
                                        command=self.choose_output, style='Ghost.TButton')
        self.output_button.grid(row=4, column=6, padx=(8, 0))

        opts = ttk.Frame(form_card, style='Panel.TFrame')
        opts.grid(row=5, column=0, columnspan=7, sticky='ew', pady=(8, 2))
        ttk.Label(opts, text='OPTIONS', style='Cyan.TLabel').pack(side='left', padx=(0, 10))
        toggle_colors = {
            'off_bg': '#1B1620', 'off_fg': '#B7A9B3', 'on_bg': '#46203A', 'on_fg': '#FFF3F8',
            'hover_bg': '#352031', 'press_bg': '#241522', 'border': '#493544', 'accent': c['pink'],
            'disabled_bg': '#17141A', 'disabled_fg': '#6E636B',
        }
        self.option_toggles = []
        for text, variable in [('子目录', self.recursive_var), ('字幕联动', self.sub_var),
                               ('语言标签', self.lang_var), ('排序编号', self.force_var)]:
            toggle = ThemeToggle(opts, text=text, variable=variable, colors=toggle_colors,
                                 font=(self.FONTS['body'], 8, 'bold'))
            toggle.pack(side='left', padx=(0, 8))
            self.option_toggles.append(toggle)
        ttk.Label(opts, text='起始集', style='MutedPanel.TLabel').pack(side='left', padx=(6, 4))
        ttk.Spinbox(opts, from_=1, to=9999, textvariable=self.start_var, width=6).pack(side='left')
        form_card.columnconfigure(1, weight=2)
        form_card.columnconfigure(5, weight=2)
        self._update_conditional_rows()

        # Action strip: edit tools stay secondary; execute is the single dominant action.
        toolbar = ttk.Frame(main, style='Toolbar.TFrame', padding=(8, 4))
        toolbar.pack(fill='x', pady=(6, 5))
        ttk.Button(toolbar, text='分组', image=self.UI_ICONS['group'], compound='left', command=self.edit_group, style='Secondary.TButton').pack(side='left', padx=(0, 6))
        ttk.Button(toolbar, text='纠正', image=self.UI_ICONS['edit'], compound='left', command=self.edit_item, style='Secondary.TButton').pack(side='left', padx=(0, 6))
        ttk.Button(toolbar, text='跳过', image=self.UI_ICONS['skip'], compound='left', command=self.toggle_skip, style='Secondary.TButton').pack(side='left', padx=(0, 6))
        ttk.Button(toolbar, text='清除', image=self.UI_ICONS['reset'], compound='left', command=self.clear_override, style='Ghost.TButton').pack(side='left', padx=(0, 6))
        self.run_btn = ttk.Button(toolbar, text='改写未来', image=self.UI_ICONS['run'], compound='left',
                                  command=self.execute, state='disabled', style='Primary.TButton')
        self.run_btn.pack(side='right')
        self.undo_btn = ttk.Button(toolbar, text='', image=self.UI_ICONS['undo'], command=self.undo,
                                   style='Danger.TButton')
        self.undo_btn.pack(side='right', padx=(0, 6))
        self.recover_btn = ttk.Button(toolbar, text='', image=self.UI_ICONS['recover'], command=self.recover,
                                      style='Ghost.TButton')
        # Recovery is exceptional: keep it hidden until an interrupted operation is actually detected.
        self.undo_btn.bind('<Enter>', lambda _e: self.detail_var.set('UNDO · 撤销上一次由本工具完成的操作。'))
        self.recover_btn.bind('<Enter>', lambda _e: self.detail_var.set('RECOVER · 恢复检测到的中断操作。'))
        self.undo_btn.bind('<Leave>', self._on_tree_leave)
        self.recover_btn.bind('<Leave>', self._on_tree_leave)

        # One compact information rail replaces the old two-row log/footer stack.
        self.detail_var = tk.StringVar(value='待确认的文件不会执行；悬停查看识别依据，双击可纠正集数。')
        self.status_var = tk.StringVar(value='选择文件夹，填写作品名，然后扫描未来记录。')
        info_rail = tk.Frame(main, bg='#121017', bd=0, highlightthickness=1, highlightbackground='#2A222B')
        info_rail.pack(fill='x', pady=(0, 5))
        tk.Label(info_rail, text='DIARY LOG', bg='#121017', fg=c['cyan'], padx=8, pady=4,
                 font=(self.FONTS['mono'], 7, 'bold')).pack(side='left')
        self.detail_entry = tk.Entry(
            info_rail, textvariable=self.detail_var, state='readonly', readonlybackground='#121017',
            fg='#B9ABB5', relief='flat', bd=0, highlightthickness=0,
            selectbackground='#4A1F39', selectforeground='#FFFFFF',
            font=(self.FONTS['body'], 8))
        self.detail_entry.pack(side='left', fill='x', expand=True, padx=(0, 6), ipady=1)
        self.copy_detail_btn = tk.Button(
            info_rail, text='COPY', command=self.copy_selected_detail, bg='#17131A', fg=c['cyan'],
            activebackground='#243134', activeforeground='#8FFFF6', relief='flat', bd=0,
            padx=7, pady=2, cursor='hand2', font=(self.FONTS['mono'], 7, 'bold'))
        self.copy_detail_btn.pack(side='right', padx=(0, 6))
        tk.Label(info_rail, textvariable=self.status_var, bg='#121017', fg='#847983', anchor='e',
                 font=(self.FONTS['mono'], 7)).pack(side='right', padx=(8, 8))

        # Preview card gets the strongest boundary and owns most of the vertical space.
        preview_outer = tk.Frame(main, bg='#4A3040', bd=0, highlightthickness=0)
        preview_outer.pack(fill='both', expand=True)
        accent = tk.Frame(preview_outer, bg='#4A3040', height=2, bd=0)
        accent.pack(fill='x')
        self.preview_status_left = tk.Frame(accent, bg='#A52C62', width=220, bd=0)
        self.preview_status_left.pack(side='left', fill='y')
        self.preview_status_right = tk.Frame(accent, bg='#285F62', width=90, bd=0)
        self.preview_status_right.pack(side='right', fill='y')
        preview_card = ttk.Frame(preview_outer, style='Panel.TFrame', padding=(8, 6))
        preview_card.pack(fill='both', expand=True, padx=1, pady=(0, 1))
        self._clip_card_corners(preview_outer, c['bg'], 4)
        preview_head = ttk.Frame(preview_card, style='Panel.TFrame')
        preview_head.pack(fill='x', pady=(0, 5))
        ttk.Label(preview_head, text='02  未来记录 / RENAME PREVIEW', style='Section.TLabel').pack(side='left')
        self.preview_legend_var = tk.StringVar(value='READY 0  ·  REVIEW 0  ·  CONFLICT 0')
        ttk.Label(preview_head, textvariable=self.preview_legend_var, style='MutedPanel.TLabel',
                  font=(self.FONTS['mono'], 8, 'bold')).pack(side='right')

        preview_shell = tk.Frame(preview_card, bg='#2C222C', bd=0, highlightthickness=1,
                                 highlightbackground='#2C222C')
        preview_shell.pack(fill='both', expand=True)
        preview = ttk.Frame(preview_shell, style='Panel.TFrame')
        preview.pack(fill='both', expand=True, padx=1, pady=1)
        cols = ('kind', 'old', 'detected', 'new', 'status')
        self.tree = ttk.Treeview(preview, columns=cols, show='tree headings', selectmode='extended')
        self.tree.heading('#0', text='GROUP')
        self.tree.column('#0', width=170, minwidth=80)
        for col, label, width in [('kind', 'TYPE', 55), ('old', 'SOURCE / 原文件名', 255),
                                  ('detected', 'MATCH', 105), ('new', 'TARGET / 目标文件名', 255),
                                  ('status', 'STATE', 200)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, minwidth=55)
        self.tree.tag_configure('group', background='#1A141D', foreground='#FFB5CF',
                                font=(self.FONTS['body'], 9, 'bold'))
        # Alternating micro-stripes act as row separators without grid-line clutter.
        stripe_colors = {
            'ready': ('#101918', '#121D1B', '#7CF6D9'),
            'warning': ('#1C1710', '#211A11', '#FFD194'),
            'error': ('#211116', '#261318', '#FF8A97'),
            'skipped': ('#121014', '#151217', '#81757E'),
            'neutral': ('#121017', '#151219', '#D8CDD5'),
        }
        for name, (even_bg, odd_bg, fg) in stripe_colors.items():
            self.tree.tag_configure(f'{name}_even', foreground=fg, background=even_bg)
            self.tree.tag_configure(f'{name}_odd', foreground=fg, background=odd_bg)
        self.tree.tag_configure('hover', background='#2B1B29', foreground='#FFFFFF')
        ybar = ttk.Scrollbar(preview, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=ybar.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        ybar.grid(row=0, column=1, sticky='ns')
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(0, weight=1)
        self.tree.bind('<Double-1>', lambda e: self.edit_item())
        self.tree.bind('<space>', lambda e: self.toggle_skip())
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.tree.bind('<Motion>', self._on_tree_motion, add='+')
        self.tree.bind('<Leave>', self._on_tree_leave, add='+')
        self.tree.bind('<Configure>', self._resize_tree_columns, add='+')
        self.tree.bind('<<TreeviewOpen>>', lambda _e: self.after_idle(self._sync_group_markers), add='+')
        self.tree.bind('<<TreeviewClose>>', lambda _e: self.after_idle(self._sync_group_markers), add='+')
        self.tree.bind('<ButtonRelease-1>', lambda _e: self.after_idle(self._sync_group_markers), add='+')
        self._hover_iid = None

        # Empty state uses a deliberately small phone illustration: enough theme, no visual takeover.
        self.empty_state = tk.Frame(preview, bg='#121017', bd=0, highlightthickness=0)
        self.empty_state.place(relx=0.5, rely=0.53, anchor='center', width=318, height=104)
        self.empty_phone_photo = self._load_photo('empty_phone.png')
        if self.empty_phone_photo:
            empty_visual = tk.Label(self.empty_state, image=self.empty_phone_photo, bg='#121017',
                                    bd=0, highlightthickness=0)
            empty_visual.pack(side='left', padx=(12, 13), pady=(12, 10))
        else:
            empty_canvas = tk.Canvas(self.empty_state, width=52, height=78, bg='#121017',
                                     highlightthickness=0, bd=0)
            empty_canvas.pack(side='left', padx=(12, 13), pady=(12, 10))
            empty_canvas.create_rectangle(8, 2, 44, 74, outline='#4D3A47', width=1)
            empty_canvas.create_rectangle(12, 10, 40, 52, outline='#24575A', fill='#0F0D12', width=1)
            empty_canvas.create_text(26, 31, text='♥', fill=c['pink'], font=(self.FONTS['body'], 15, 'bold'))
            empty_canvas.create_line(17, 59, 35, 59, fill='#38D6D0', width=1)
            empty_canvas.create_oval(23, 65, 29, 71, outline='#715C69', width=1)
        empty_text = tk.Frame(self.empty_state, bg='#121017')
        empty_text.pack(side='left', fill='both', expand=True, pady=(13, 8), padx=(0, 8))
        self.empty_title_var = tk.StringVar(value='尚未读取未来')
        self.empty_sub_var = tk.StringVar(value='选择文件夹并扫描后，重命名预览会显示在这里。')
        tk.Label(empty_text, textvariable=self.empty_title_var, bg='#121017', fg='#EADFE7',
                 font=(self.FONTS['display'], 11, 'bold'), anchor='w').pack(fill='x')
        tk.Label(empty_text, text='WAITING FOR DIARY DATA', bg='#121017', fg='#6FCBC5',
                 font=(self.FONTS['mono'], 7, 'bold'), anchor='w').pack(fill='x', pady=(2, 6))
        tk.Label(empty_text, textvariable=self.empty_sub_var, bg='#121017', fg='#887D85',
                 wraplength=220, justify='left', anchor='w', font=(self.FONTS['body'], 8)).pack(fill='x')

        for variable in [self.folder_var, self.title_var, self.season_var, self.template_name_var, self.template_var,
                         self.mode_var, self.output_var, self.recursive_var, self.sub_var,
                         self.lang_var, self.force_var, self.start_var]:
            variable.trace_add('write', self.settings_changed)
        self._set_chrome_state('WAITING', 'neutral')
