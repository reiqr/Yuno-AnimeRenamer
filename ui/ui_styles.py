from tkinter import ttk


class StyleMixin:
    def _configure_theme(self):
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
        self.UI_ICONS = {}
        self.FONTS = {
            'body': self._pick_font('Microsoft YaHei UI', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans SC', 'PingFang SC', 'Segoe UI'),
            'display': self._pick_font('Microsoft YaHei', 'Microsoft YaHei UI', 'Microsoft JhengHei UI', 'Segoe UI'),
            'latin': self._pick_font('Segoe UI Variable Display', 'Segoe UI Semibold', 'Bahnschrift', 'Segoe UI', 'Arial'),
            'jp': self._pick_font('Yu Gothic UI', 'Yu Gothic', 'Meiryo UI', 'Noto Sans CJK JP', 'Noto Sans JP', 'Microsoft YaHei UI'),
            'mono': self._pick_font('Cascadia Code', 'Cascadia Mono', 'Consolas', 'JetBrains Mono', 'DejaVu Sans Mono'),
        }
        self.option_add('*Font', (self.FONTS['body'], 9))
        self.UI_ICONS = {
            'folder': self._make_pixel_icon('folder', c['pink']),
            'scan': self._make_pixel_icon('scan', '#FFFFFF'),
            'title': self._make_pixel_icon('title', '#D985AC'),
            'season': self._make_pixel_icon('season', c['cyan']),
            'rule': self._make_pixel_icon('rule', '#B987C7'),
            'mode': self._make_pixel_icon('mode', '#C095B0'),
            'target': self._make_pixel_icon('target', c['cyan']),
            'group': self._make_pixel_icon('group', '#DDA5C0'),
            'edit': self._make_pixel_icon('edit', c['pink']),
            'skip': self._make_pixel_icon('skip', c['warning']),
            'reset': self._make_pixel_icon('reset', '#A89BA6'),
            'recover': self._make_pixel_icon('recover', c['cyan']),
            'undo': self._make_pixel_icon('undo', '#FF8B99'),
            'run': self._make_pixel_icon('run', '#FFFFFF'),
        }
        self.option_add('*TCombobox*Listbox.background', c['panel3'])
        self.option_add('*TCombobox*Listbox.foreground', c['text'])
        self.option_add('*TCombobox*Listbox.selectBackground', '#4A1F39')
        self.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')
        self.option_add('*Menu.background', c['panel2'])
        self.option_add('*Menu.foreground', c['text'])
        self.option_add('*Menu.activeBackground', '#4A1F39')
        self.option_add('*Menu.activeForeground', '#FFFFFF')

        style = ttk.Style(self)
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        style.configure('.',
                        background=c['bg'], foreground=c['text'],
                        fieldbackground=c['panel2'], bordercolor=c['border'],
                        lightcolor=c['border'], darkcolor=c['border'],
                        font=(self.FONTS['body'], 9))
        style.configure('App.TFrame', background=c['bg'])
        style.configure('Panel.TFrame', background=c['panel'])
        style.configure('Card.TFrame', background=c['panel2'])
        style.configure('Toolbar.TFrame', background='#17131B', borderwidth=1, relief='solid',
                        bordercolor='#352936', lightcolor='#352936', darkcolor='#352936')
        style.configure('Chrome.TFrame', background=c['panel'], borderwidth=1, relief='solid',
                        bordercolor='#342934', lightcolor='#342934', darkcolor='#342934')
        style.configure('Sidebar.TFrame', background='#110C14')
        style.configure('TLabel', background=c['bg'], foreground=c['text'])
        style.configure('Panel.TLabel', background=c['panel'], foreground=c['text'])
        style.configure('Card.TLabel', background=c['panel2'], foreground=c['text'])
        style.configure('Muted.TLabel', background=c['bg'], foreground=c['muted'])
        style.configure('MutedPanel.TLabel', background=c['panel'], foreground=c['muted'])
        style.configure('Sidebar.TLabel', background='#110C14', foreground=c['text'])
        style.configure('SidebarMuted.TLabel', background='#110C14', foreground='#A98E9E')
        style.configure('Hero.TLabel', background='#110C14', foreground='#FFF1F7',
                        font=(self.FONTS['display'], 18, 'bold'))
        style.configure('HeroSub.TLabel', background='#110C14', foreground=c['pink'],
                        font=(self.FONTS['mono'], 8, 'bold'))
        style.configure('Title.TLabel', background=c['bg'], foreground=c['text'],
                        font=(self.FONTS['display'], 18, 'bold'))
        style.configure('Section.TLabel', background=c['panel'], foreground=c['text'],
                        font=(self.FONTS['body'], 10, 'bold'))
        style.configure('Accent.TLabel', background=c['panel'], foreground=c['pink'])
        style.configure('Cyan.TLabel', background=c['panel2'], foreground=c['cyan'],
                        font=(self.FONTS['mono'], 8, 'bold'))

        style.configure('TEntry', padding=(9, 7), relief='flat', borderwidth=1,
                        foreground=c['text'], fieldbackground=c['panel3'],
                        insertcolor=c['pink'], font=(self.FONTS['body'], 9))
        style.map('TEntry', fieldbackground=[('disabled', '#17131A')],
                  foreground=[('disabled', '#706670')])
        style.configure('TCombobox', padding=(9, 7), arrowsize=12, relief='flat', borderwidth=1,
                        foreground=c['text'], fieldbackground=c['panel3'], arrowcolor=c['pink'],
                        bordercolor='#5A3146', lightcolor='#5A3146', darkcolor='#5A3146',
                        font=(self.FONTS['body'], 9))
        style.map('TCombobox', fieldbackground=[('readonly', c['panel3'])],
                  selectbackground=[('readonly', c['panel3'])],
                  selectforeground=[('readonly', c['text'])])
        style.configure('TSpinbox', padding=(9, 7), arrowsize=10, relief='flat', borderwidth=1,
                        foreground=c['text'], fieldbackground=c['panel3'],
                        arrowcolor=c['pink'], font=(self.FONTS['body'], 9))
        style.map('TEntry', bordercolor=[('focus', c['pink']), ('!focus', '#4A3341')],
                  lightcolor=[('focus', c['pink']), ('!focus', '#4A3341')],
                  darkcolor=[('focus', c['pink']), ('!focus', '#4A3341')])
        style.map('TCombobox', bordercolor=[('focus', c['pink']), ('active', '#77405C'), ('!focus', '#4A3341')],
                  lightcolor=[('focus', c['pink']), ('!focus', '#4A3341')],
                  darkcolor=[('focus', c['pink']), ('!focus', '#4A3341')],
                  arrowcolor=[('active', '#FFFFFF'), ('readonly', c['pink'])])
        style.map('TSpinbox', bordercolor=[('focus', c['cyan']), ('active', '#356C6C'), ('!focus', '#4A3341')],
                  lightcolor=[('focus', c['cyan']), ('!focus', '#4A3341')],
                  darkcolor=[('focus', c['cyan']), ('!focus', '#4A3341')],
                  arrowcolor=[('active', '#FFFFFF'), ('!active', c['cyan'])])
        style.configure('Option.TCheckbutton', background=c['panel'], foreground='#DCCFD8', padding=(2, 2))
        style.map('Option.TCheckbutton', background=[('active', c['panel'])],
                  foreground=[('active', '#FFFFFF'), ('selected', '#FFF0F6')],
                  indicatorcolor=[('selected', c['pink2']), ('!selected', '#493943')])

        style.configure('TCheckbutton', background=c['panel'], foreground=c['text'], padding=2)
        style.map('TCheckbutton', background=[('active', c['panel'])],
                  foreground=[('active', c['text'])],
                  indicatorcolor=[('selected', c['pink']), ('!selected', '#5D505A')])

        style.configure('TButton', padding=(12, 8), relief='flat', borderwidth=1,
                        background=c['panel3'], foreground=c['text'], bordercolor='#523545',
                        lightcolor='#523545', darkcolor='#523545')
        style.map('TButton', background=[('active', '#332536'), ('pressed', '#241A28'), ('disabled', '#17141A')],
                  foreground=[('disabled', '#655C65')])
        style.configure('Primary.TButton', padding=(16, 9), background=c['pink2'],
                        foreground='#FFFFFF', bordercolor=c['pink'])
        style.map('Primary.TButton', background=[('active', c['pink']), ('pressed', '#B61F5C'), ('disabled', '#442537')],
                  foreground=[('disabled', '#957A88')])
        style.configure('Danger.TButton', background='#3A1820', foreground='#FF8B99', bordercolor='#702535',
                        lightcolor='#702535', darkcolor='#702535')
        style.map('Danger.TButton', background=[('pressed', '#2A1017'), ('active', '#52202B')],
                  foreground=[('pressed', '#FFFFFF')])
        style.configure('Ghost.TButton', background=c['panel2'], foreground=c['muted'], bordercolor='#483340',
                        lightcolor='#483340', darkcolor='#483340')
        style.map('Ghost.TButton', background=[('pressed', '#171119'), ('active', c['panel3'])],
                  foreground=[('pressed', '#FFFFFF'), ('active', c['text'])])
        style.configure('Secondary.TButton', background='#231923', foreground='#EEDCE7', bordercolor='#68405A',
                        lightcolor='#68405A', darkcolor='#68405A', padding=(9, 7))
        style.map('Secondary.TButton', background=[('pressed', '#1B121B'), ('active', '#352234'), ('disabled', '#17141A')],
                  foreground=[('pressed', '#FFFFFF'), ('active', '#FFFFFF'), ('disabled', '#655C65')],
                  bordercolor=[('active', '#A44A76'), ('pressed', '#7C365B')])
        style.configure('Cyan.TButton', background='#143638', foreground='#74FFF3', bordercolor='#246B6A',
                        lightcolor='#246B6A', darkcolor='#246B6A')
        style.map('Cyan.TButton', background=[('pressed', '#0D292B'), ('active', '#1B4A4A')],
                  foreground=[('pressed', '#FFFFFF')])

        style.configure('Treeview', rowheight=28, relief='flat', borderwidth=0,
                        background='#121017', fieldbackground='#121017', foreground='#EDE5EC',
                        font=(self.FONTS['body'], 9))
        style.configure('Treeview.Heading', background='#211923', foreground='#F7EAF3',
                        relief='flat', borderwidth=0, padding=(5, 7), font=(self.FONTS['body'], 9, 'bold'))
        style.map('Treeview', background=[('selected', '#6A2850')], foreground=[('selected', '#FFFFFF')])
        style.map('Treeview.Heading', background=[('active', '#38243A')], foreground=[('active', '#FFFFFF')])
        style.configure('Vertical.TScrollbar', background='#251B28', troughcolor='#0F0D12', arrowcolor='#B89EAE',
                        bordercolor='#0F0D12', lightcolor='#251B28', darkcolor='#251B28', arrowsize=9, width=10)
        style.map('Vertical.TScrollbar', background=[('active', c['pink2']), ('pressed', c['pink'])],
                  arrowcolor=[('active', '#FFFFFF')])
        style.configure('Horizontal.TScrollbar', background='#251B28', troughcolor='#0F0D12', arrowcolor='#B89EAE',
                        bordercolor='#0F0D12', lightcolor='#251B28', darkcolor='#251B28', arrowsize=9, width=10)
        style.map('Horizontal.TScrollbar', background=[('active', c['pink2']), ('pressed', c['pink'])],
                  arrowcolor=[('active', '#FFFFFF')])
