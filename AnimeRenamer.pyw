# -*- coding: utf-8 -*-
from __future__ import annotations

import sys


def _enable_windows_dpi_awareness():
    """Prevent Windows from bitmap-scaling Tk, which makes the whole UI blurry."""
    if not sys.platform.startswith('win'):
        return
    try:
        import ctypes
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            return
        except Exception:
            pass
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return
        except Exception:
            pass
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


_enable_windows_dpi_awareness()

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from renamer_core import (VERSION, READY, GroupSettings, build_plan, parse_override,
                          execute_plan, undo_last, recover_pending, pending_operation)
from ui_actions import ActionMixin
from ui_constants import TEMPLATES
from ui_dialogs import DialogMixin, GroupDialog
from ui_layout import LayoutMixin
from ui_styles import StyleMixin
from ui_theme import ThemeMixin, ThemeToggle
from ui_view import ViewMixin


class App(ThemeMixin, DialogMixin, StyleMixin, LayoutMixin, ViewMixin, ActionMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'AnimeRenamer {VERSION} · 未来日记主题')
        self._set_initial_geometry()
        self.plan = []
        self.overrides, self.groups, self.skipped = {}, {}, set()
        self.busy, self.dirty = False, True
        self.source_context = ''
        self.group_nodes = {}
        self._busy_anim_id = None
        self._busy_anim_step = 0
        self._status_mode = 'neutral'
        self._test_dialog_mode = (__name__ == 'test_ui')
        self._build_ui()
        try:
            icon = self._load_photo('app_icon.png')
            if icon:
                self.iconphoto(True, icon)
        except tk.TclError:
            pass
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(80, self._apply_window_chrome)
        self.after(150, self.check_recovery)

    def _set_initial_geometry(self):
        """Open at a compact, centered size that adapts to the current monitor."""
        self.update_idletasks()
        sw = max(1024, self.winfo_screenwidth())
        sh = max(720, self.winfo_screenheight())
        # DPI awareness keeps this a genuinely smaller window instead of a low-resolution
        # window bitmap that Windows later stretches.
        width = min(1160, max(1000, int(sw * 0.66)))
        height = min(720, max(680, int(sh * 0.72)))
        width = min(width, max(960, sw - 70))
        height = min(height, max(640, sh - 60))
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2 - 12)
        self.geometry(f'{width}x{height}+{x}+{y}')
        self.minsize(960, 640)


<<<<<<< Updated upstream
=======
    @staticmethod
    def _colorref(hex_color):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return 0
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (b << 16) | (g << 8) | r

    def _apply_window_chrome(self):
        """Use a dark Windows title bar when the platform supports it."""
        if not sys.platform.startswith('win'):
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            dark = ctypes.c_int(1)
            attrs = [20, 19]  # Win11 / Win10 immersive dark mode ids.
            for attr in attrs:
                try:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(dark), ctypes.sizeof(dark))
                except OSError:
                    pass
            for attr, color in [(35, self._colorref('#110C14')), (34, self._colorref('#110C14')), (36, self._colorref('#FFF1F7'))]:
                try:
                    value = ctypes.c_int(color)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
                except OSError:
                    pass
        except Exception:
            pass

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

    def _make_pixel_icon(self, kind, color='#FF6EA3', size=14):
        """Create a tiny transparent pixel icon in-memory; no extra asset/font dependency."""
        img = tk.PhotoImage(width=size, height=size)

        def px(x0, y0, x1=None, y1=None, fill=None):
            x1 = x0 + 1 if x1 is None else x1
            y1 = y0 + 1 if y1 is None else y1
            img.put(fill or color, to=(x0, y0, x1, y1))

        # Coordinates are deliberately blocky: they stay crisp on Tk/Windows scaling.
        if kind == 'folder':
            px(1, 4, 13, 12); px(2, 2, 6, 5); px(2, 5, 12, 11, '#2A1A24'); px(3, 6, 11, 10, '#3B2634')
        elif kind == 'scan':
            px(2, 2, 5, 3); px(2, 2, 3, 5); px(9, 2, 12, 3); px(11, 2, 12, 5)
            px(2, 9, 3, 12); px(2, 11, 5, 12); px(11, 9, 12, 12); px(9, 11, 12, 12); px(5, 6, 9, 8)
        elif kind == 'title':
            px(2, 3, 12, 4); px(6, 4, 8, 12); px(4, 11, 10, 12)
        elif kind == 'season':
            px(2, 2, 12, 12); px(3, 4, 11, 11, '#231821'); px(3, 5, 11, 6); px(5, 1, 6, 4); px(9, 1, 10, 4); px(5, 7, 7, 9)
        elif kind == 'rule':
            px(2, 2, 12, 3); px(2, 6, 10, 7); px(2, 10, 12, 11); px(10, 5, 12, 8)
        elif kind == 'mode':
            px(2, 4, 8, 10); px(6, 2, 12, 8); px(7, 3, 11, 7, '#231821')
        elif kind == 'target':
            px(2, 2, 12, 3); px(2, 3, 3, 12); px(2, 11, 12, 12); px(6, 5, 12, 6); px(9, 3, 12, 8)
        elif kind == 'group':
            px(2, 2, 6, 6); px(8, 2, 12, 6); px(5, 8, 9, 12); px(3, 6, 4, 9); px(10, 6, 11, 9); px(3, 8, 11, 9)
        elif kind == 'edit':
            px(2, 10, 5, 12); px(4, 8, 11, 11); px(9, 3, 12, 6); px(6, 6, 11, 10)
        elif kind == 'skip':
            px(2, 6, 10, 8); px(8, 3, 12, 11); px(10, 5, 13, 9)
        elif kind == 'reset':
            px(3, 3, 10, 4); px(2, 4, 4, 10); px(3, 10, 10, 12); px(9, 8, 12, 11); px(1, 2, 5, 6)
        elif kind == 'recover':
            px(2, 3, 11, 4); px(2, 3, 3, 10); px(2, 9, 9, 11); px(8, 7, 11, 11); px(9, 5, 13, 9)
        elif kind == 'undo':
            px(4, 3, 11, 4); px(3, 4, 5, 10); px(4, 9, 11, 11); px(1, 2, 5, 6)
        elif kind == 'run':
            px(3, 2, 5, 12); px(5, 3, 7, 11); px(7, 4, 9, 10); px(9, 5, 11, 9); px(11, 6, 13, 8)
        elif kind == 'clear':
            px(3, 3, 11, 4); px(4, 4, 10, 12); px(2, 2, 12, 3); px(5, 1, 9, 2)
        else:
            px(3, 3, 11, 11); px(5, 5, 9, 9, '#231821')
        self._theme_images.append(img)
        return img

    def _draw_banner(self, _event=None):
        canvas = getattr(self, 'banner_canvas', None)
        if not canvas:
            return
        canvas.delete('overlay')
        width = max(canvas.winfo_width(), 720)
        banner = getattr(self, 'banner_photo_wide', None) if width >= 840 else getattr(self, 'banner_photo', None)
        if banner:
            canvas.create_image(0, 0, image=banner, anchor='nw', tags='overlay')
        # Dark veil on the right keeps text readable without altering the asset.
        height = max(82, canvas.winfo_height())
        canvas.create_rectangle(max(360, int(width * 0.44)), 0, width, height,
                                fill='#0D0910', stipple='gray50', outline='', tags='overlay')
        tx = max(470, int(width * 0.58))
        canvas.create_text(tx, 17, text='ANIME RENAMER', anchor='w', fill='#FFF2F7',
                           font=(self.FONTS['latin'], 17, 'bold'), tags='overlay')
        canvas.create_text(tx, 37, text='未来日记 · RENAME TERMINAL', anchor='w', fill='#FF6EA3',
                           font=(self.FONTS['body'], 9, 'bold'), tags='overlay')
        canvas.create_text(tx, 56, text='01 SCAN   →   02 CHECK   →   03 REWRITE', anchor='w', fill='#C9BCC5',
                           font=(self.FONTS['mono'], 7, 'bold'), tags='overlay')
        line_y = min(height - 8, 70)
        canvas.create_line(tx, line_y, min(width - 24, tx + 170), line_y,
                           fill='#FF4F91', width=2, tags='overlay')
        canvas.create_line(min(width - 24, tx + 170), line_y, min(width - 24, tx + 280), line_y,
                           fill='#38D6D0', width=2, tags='overlay')
        canvas.create_rectangle(0, height - 3, width, height, fill='#0A080D', outline='', tags='overlay')
        canvas.create_line(0, height - 3, min(width, int(width * 0.38)), height - 3, fill='#8C2B59', width=1, tags='overlay')
        canvas.create_line(max(0, int(width * 0.72)), height - 3, width, height - 3, fill='#245A5A', width=1, tags='overlay')

    def _legacy_dialog_mode(self):
        # The bundled GUI tests monkey-patch tkinter dialogs. Keep that path intact.
        return globals().get('__name__') == 'test_ui'

    def _center_popup(self, popup, width=470):
        popup.update_idletasks()
        height = popup.winfo_reqheight()
        try:
            px = self.winfo_rootx()
            py = self.winfo_rooty()
            pw = self.winfo_width()
            ph = self.winfo_height()
            x = px + max(10, (pw - width) // 2)
            y = py + max(10, (ph - height) // 2)
        except tk.TclError:
            x = max(0, (self.winfo_screenwidth() - width) // 2)
            y = max(0, (self.winfo_screenheight() - height) // 2)
        popup.geometry(f'{width}x{height}+{x}+{y}')

    def _theme_modal(self, title, message, *, kind='info', confirm=False,
                     prompt=False, initial=''):
        c = self.COLORS
        accents = {
            'info': (c['cyan'], 'INFO'),
            'success': (c['success'], 'DONE'),
            'warning': (c['warning'], 'CHECK'),
            'error': (c['error'], 'ERROR'),
            'question': (c['pink'], 'CONFIRM'),
        }
        accent, badge = accents.get(kind, accents['info'])
        result = {'value': None if prompt else False}

        win = tk.Toplevel(self)
        win.withdraw()
        win.overrideredirect(True)
        win.transient(self)
        win.configure(bg=accent)
        try:
            win.attributes('-alpha', 0.995)
        except tk.TclError:
            pass

        outer = tk.Frame(win, bg=accent, bd=0, padx=1, pady=1)
        outer.pack(fill='both', expand=True)
        panel = tk.Frame(outer, bg=c['panel'], bd=0)
        panel.pack(fill='both', expand=True)

        head = tk.Frame(panel, bg='#17111A', height=44)
        head.pack(fill='x')
        head.pack_propagate(False)
        tk.Frame(head, bg=accent, width=5).pack(side='left', fill='y')
        tk.Label(head, text=badge, bg='#17111A', fg=accent,
                 font=(self.FONTS['mono'], 8, 'bold')).pack(side='left', padx=(12, 9))
        tk.Label(head, text=title, bg='#17111A', fg=c['text'],
                 font=(self.FONTS['body'], 11, 'bold')).pack(side='left')
        tk.Label(head, text='MIRAI NIKKI', bg='#17111A', fg='#7D6977',
                 font=(self.FONTS['mono'], 7, 'bold')).pack(side='right', padx=14)

        body = tk.Frame(panel, bg=c['panel'], padx=22, pady=18)
        body.pack(fill='both', expand=True)
        tk.Label(body, text=message, bg=c['panel'], fg=c['text'], justify='left',
                 anchor='w', wraplength=420,
                 font=(self.FONTS['body'], 10)).pack(fill='x')

        entry = None
        if prompt:
            entry_box = tk.Frame(body, bg='#5A3146', padx=1, pady=1)
            entry_box.pack(fill='x', pady=(15, 0))
            entry = tk.Entry(entry_box, bg=c['panel3'], fg=c['text'], insertbackground=accent,
                             relief='flat', bd=0, font=(self.FONTS['body'], 10))
            entry.pack(fill='x', ipady=8, padx=1, pady=1)
            entry.insert(0, initial or '')
            entry.select_range(0, 'end')

        actions = tk.Frame(panel, bg=c['panel'], padx=18, pady=0)
        actions.pack(fill='x', pady=(0, 16))

        def close(value):
            result['value'] = value
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()

        def make_button(text, command, primary=False, danger=False):
            bg = c['pink2'] if primary else ('#3A1820' if danger else c['panel3'])
            fg = '#FFFFFF' if primary else ('#FF9BA7' if danger else c['text'])
            active = c['pink'] if primary else ('#52202B' if danger else '#332536')
            button = tk.Button(actions, text=text, command=command, bg=bg, fg=fg,
                               activebackground=active, activeforeground='#FFFFFF',
                               relief='flat', bd=0, padx=16, pady=8,
                               cursor='hand2', font=(self.FONTS['body'], 9, 'bold'))
            pressed = '#1E111A' if not primary and not danger else ('#981B4B' if primary else '#281018')
            button.bind('<Enter>', lambda _e, b=button, col=active: b.configure(bg=col))
            button.bind('<Leave>', lambda _e, b=button, col=bg: b.configure(bg=col))
            button.bind('<ButtonPress-1>', lambda _e, b=button, col=pressed: b.configure(bg=col))
            button.bind('<ButtonRelease-1>', lambda _e, b=button, col=active: b.configure(bg=col))
            return button

        if prompt:
            make_button('取消', lambda: close(None)).pack(side='right', padx=(8, 0))
            make_button('确认', lambda: close(entry.get()), primary=True).pack(side='right')
        elif confirm:
            make_button('取消', lambda: close(False)).pack(side='right', padx=(8, 0))
            make_button('继续执行', lambda: close(True), primary=True).pack(side='right')
        else:
            make_button('确定', lambda: close(True), primary=(kind in ('success', 'info')),
                        danger=(kind == 'error')).pack(side='right')

        win.bind('<Escape>', lambda _e: close(None if prompt else False))
        if prompt and entry is not None:
            win.bind('<Return>', lambda _e: close(entry.get()))
        elif confirm:
            win.bind('<Return>', lambda _e: close(True))
        else:
            win.bind('<Return>', lambda _e: close(True))

        self._center_popup(win)
        win.deiconify()
        win.lift()
        win.grab_set()
        if entry is not None:
            entry.focus_set()
        else:
            win.focus_set()
        self.wait_window(win)
        return result['value']

    def _alert(self, title, message, *, kind='info'):
        if self._legacy_dialog_mode():
            func = messagebox.showerror if kind == 'error' else (
                messagebox.showwarning if kind == 'warning' else messagebox.showinfo)
            return func(title, message, parent=self)
        return self._theme_modal(title, message, kind=kind)

    def _confirm(self, title, message, *, kind='question'):
        if self._legacy_dialog_mode():
            return messagebox.askyesno(title, message, parent=self)
        return bool(self._theme_modal(title, message, kind=kind, confirm=True))

    def _prompt(self, title, message, *, initial=''):
        if self._legacy_dialog_mode():
            return simpledialog.askstring(title, message, initialvalue=initial, parent=self)
        return self._theme_modal(title, message, kind='question', prompt=True, initial=initial)

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
        self.UI_ICONS = {}
        self.FONTS = {
            # Use only Windows/system fonts: no external font files are required.
            'body': self._pick_font('Microsoft YaHei UI', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Noto Sans SC', 'PingFang SC', 'Segoe UI'),
            'display': self._pick_font('Microsoft YaHei UI', 'Microsoft YaHei', 'Microsoft JhengHei UI', 'Segoe UI'),
            'latin': self._pick_font('Bahnschrift', 'Segoe UI Variable Display', 'Segoe UI Semibold', 'Segoe UI', 'Arial'),
            'jp': self._pick_font('Yu Gothic UI', 'Yu Gothic', 'Meiryo UI', 'Noto Sans CJK JP', 'Noto Sans JP', 'Microsoft YaHei UI'),
            'mono': self._pick_font('Cascadia Mono', 'Cascadia Code', 'Consolas', 'JetBrains Mono', 'DejaVu Sans Mono'),
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

        # Base controls
        style.configure('.',
                        background=c['bg'], foreground=c['text'],
                        fieldbackground=c['panel2'], bordercolor=c['border'],
                        lightcolor=c['border'], darkcolor=c['border'],
                        font=(self.FONTS['body'], 10))
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
                        font=(self.FONTS['body'], 11, 'bold'))
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
        # Focus-aware controls: a thin pink/cyan rim replaces the default square system look.
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
                        relief='flat', borderwidth=0, padding=(5, 7), font=(self.FONTS['body'], 8, 'bold'))
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

    def _clip_card_corners(self, frame, outside=None, size=4):
        """Fake softened/chamfered card corners without a heavy custom widget."""
        if outside is None:
            outside = self.COLORS.get('bg', '#0D0B11')
        corners = [
            dict(x=0, y=0, anchor='nw'),
            dict(relx=1, y=0, anchor='ne'),
            dict(x=0, rely=1, anchor='sw'),
            dict(relx=1, rely=1, anchor='se'),
        ]
        for spec in corners:
            chip = tk.Frame(frame, bg=outside, width=size, height=size, bd=0, highlightthickness=0)
            chip.place(**spec)
            chip.lift()

    def _sync_group_markers(self):
        if not hasattr(self, 'tree'):
            return
        for iid in self.tree.get_children(''):
            if iid not in self.group_nodes or not self.tree.exists(iid):
                continue
            text = str(self.tree.item(iid, 'text'))
            if text.startswith(('▾', '▸')):
                label = text[1:].lstrip()
            else:
                label = text.lstrip()
            marker = '▾' if bool(self.tree.item(iid, 'open')) else '▸'
            self.tree.item(iid, text=f'{marker}  {label}')

    def _resize_tree_columns(self, _event=None):
        """Distribute preview columns by the actual viewport width."""
        if not hasattr(self, 'tree'):
            return
        width = max(620, self.tree.winfo_width() - 12)
        specs = {
            '#0': (0.12, 80), 'kind': (0.06, 46), 'old': (0.29, 155),
            'detected': (0.10, 72), 'new': (0.29, 155), 'status': (0.14, 95),
        }
        for col, (ratio, minimum) in specs.items():
            try:
                self.tree.column(col, width=max(minimum, int(width * ratio)), minwidth=minimum)
            except tk.TclError:
                pass

    def _on_tree_select(self, _event=None):
        self._sync_selection_markers()
        self.show_detail()

    def _sync_selection_markers(self):
        # Reuse the tree column as a slim selection rail instead of drawing overlays.
        if not hasattr(self, 'tree'):
            return
        selected = set(self.tree.selection())
        for group_iid in self.tree.get_children(''):
            for row_iid in self.tree.get_children(group_iid):
                if not self.tree.exists(row_iid):
                    continue
                self.tree.item(row_iid, text='┃' if row_iid in selected else '')

    def _on_tree_motion(self, event):
        iid = self.tree.identify_row(event.y)
        if iid == self._hover_iid:
            return
        self._clear_tree_hover()
        if not iid:
            return
        tags = list(self.tree.item(iid, 'tags'))
        if 'hover' not in tags:
            tags.append('hover')
            self.tree.item(iid, tags=tuple(tags))
        self._hover_iid = iid
        if iid.startswith('r'):
            try:
                item = self.plan[int(iid[1:])]
                self.detail_var.set(f'悬停预览 · {item.reason}（规则评分 {item.confidence}/100）')
            except (ValueError, IndexError):
                pass
        elif iid in self.group_nodes:
            self.detail_var.set('分组行 · 单击可选择整组，使用 GROUP 按钮设置该组的作品名、季度或起始集。')

    def _clear_tree_hover(self):
        iid = getattr(self, '_hover_iid', None)
        if iid and self.tree.exists(iid):
            tags = tuple(tag for tag in self.tree.item(iid, 'tags') if tag != 'hover')
            self.tree.item(iid, tags=tags)
        self._hover_iid = None

    def _on_tree_leave(self, _event=None):
        self._clear_tree_hover()
        if self.tree.selection():
            self.show_detail()
        else:
            self.detail_var.set('待确认的文件不会执行；悬停查看依据，双击可纠正集数。')

    def _set_empty_state(self, title=None, subtitle=None, visible=True):
        if not hasattr(self, 'empty_state'):
            return
        if title is not None:
            self.empty_title_var.set(title)
        if subtitle is not None:
            self.empty_sub_var.set(subtitle)
        if visible:
            self.empty_state.place(relx=0.5, rely=0.53, anchor='center', width=318, height=104)
            self.empty_state.lift()
        else:
            self.empty_state.place_forget()

    def _set_chrome_state(self, text, mode='info'):
        palette = {
            'info': ('#132223', '#74FFF3', '#275A60'),
            'success': ('#11241E', '#7CF6D9', '#2E6F61'),
            'warning': ('#2A2013', '#FFD194', '#765527'),
            'error': ('#2A1419', '#FF929E', '#7A3040'),
            'dirty': ('#281521', '#FF91BA', '#7A3655'),
            'busy': ('#211A32', '#C2AEFF', '#5A4B83'),
            'neutral': ('#19161C', '#A89BA6', '#3A3239'),
        }
        bg, fg, border = palette.get(mode, palette['info'])
        self._status_mode = mode
        if hasattr(self, 'chrome_state_var'):
            self.chrome_state_var.set(text)
        if hasattr(self, 'chrome_state_label'):
            self.chrome_state_label.configure(bg=bg, fg=fg, highlightbackground=border)
        if hasattr(self, 'footer_state_label'):
            self.footer_state_label.configure(fg=fg)
        if hasattr(self, 'chrome_status_line'):
            self.chrome_status_line.configure(bg=border)
        if hasattr(self, 'form_status_line'):
            self.form_status_line.configure(bg=border)
        if hasattr(self, 'preview_status_left'):
            self.preview_status_left.configure(bg=border)
        if hasattr(self, 'preview_status_right'):
            self.preview_status_right.configure(bg=fg if mode in ('success', 'busy') else '#285F62')

    def _update_conditional_rows(self):
        """Keep the default window compact; reveal advanced rows only when needed."""
        if hasattr(self, 'template_entry'):
            custom = self.template_name_var.get() == '自定义'
            if custom:
                self.template_label.grid(row=3, column=0, sticky='w', padx=(0, 8), pady=4)
                self.template_entry.grid(row=3, column=1, columnspan=5, sticky='ew', pady=4)
                self.template_hint.grid(row=3, column=6, sticky='w', padx=(8, 0))
            else:
                self.template_label.grid_remove()
                self.template_entry.grid_remove()
                self.template_hint.grid_remove()
            self.template_entry.configure(state='normal' if custom else 'disabled')
        if hasattr(self, 'output_entry'):
            copy_mode = self.mode_var.get() != '原地重命名'
            if copy_mode:
                self.output_label.grid(row=4, column=2, sticky='w', padx=(0, 8), pady=4)
                self.output_entry.grid(row=4, column=3, columnspan=3, sticky='ew')
                self.output_button.grid(row=4, column=6, padx=(8, 0))
            else:
                self.output_label.grid_remove()
                self.output_entry.grid_remove()
                self.output_button.grid_remove()

    def _start_busy_animation(self):
        self._stop_busy_animation()
        self._busy_anim_step = 0
        self._busy_anim_tick()

    def _busy_anim_tick(self):
        if not self.busy:
            self._busy_anim_id = None
            return
        frames = ('PROCESSING ·', 'PROCESSING ··', 'PROCESSING ···')
        self._set_chrome_state(frames[self._busy_anim_step % len(frames)], 'busy')
        self._busy_anim_step += 1
        self._busy_anim_id = self.after(320, self._busy_anim_tick)

    def _stop_busy_animation(self):
        callback = getattr(self, '_busy_anim_id', None)
        if callback is not None:
            try:
                self.after_cancel(callback)
            except tk.TclError:
                pass
        self._busy_anim_id = None

    def settings_changed(self, *_):
        self._update_conditional_rows()
        if self.folder_var.get() != self.source_context:
            self.groups.clear()
            self.overrides.clear()
            self.skipped.clear()
            self.source_context = self.folder_var.get()
        self.dirty = True
        self.run_btn.state(['disabled'])
        self.status_var.set('设置已改变，请刷新预览后执行。')
        self._set_chrome_state('NEEDS REFRESH', 'dirty')

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
        self._update_conditional_rows()

    def _controls(self, widget):
        for child in widget.winfo_children():
            if isinstance(child, (ttk.Entry, ttk.Button, ttk.Checkbutton, ttk.Combobox, ttk.Spinbox, ThemeToggle)):
                yield child
            yield from self._controls(child)

    def _start_task(self, function, completed):
        if self.busy:
            return
        self.busy = True
        self._start_busy_animation()
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
                    self._stop_busy_animation()
                    for widget, state in states:
                        widget.state(['!disabled'])
                        widget.state(state)
                    if kind == 'error':
                        self.dirty = True
                        self._alert('操作失败', result, kind='error')
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
            self._alert('设置有误', str(exc), kind='error')
            return
        self.status_var.set('正在识别文件…')
        self._set_empty_state('正在读取未来…', '正在分析文件名、字幕关联和分组，请稍候。', visible=True)
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
                self.tree.insert('', 'end', iid=node, text='▾  ' + label, open=True, tags=('group',))
            status = item.status
            if status.startswith(('冲突', '错误')):
                base_tag, shown_status = 'error', '!!  ' + status
            elif status.startswith('待'):
                base_tag, shown_status = 'warning', '?   ' + status
            elif status.startswith('已跳过'):
                base_tag, shown_status = 'skipped', '--  ' + status
            elif status == READY:
                base_tag, shown_status = 'ready', 'OK  可执行'
            else:
                base_tag, shown_status = 'neutral', status
            stripe = 'even' if index % 2 == 0 else 'odd'
            tag = f'{base_tag}_{stripe}'
            media = 'VIDEO' if item.kind == '视频' else ('SUB' if item.kind == '字幕' else str(item.kind).upper())
            self.tree.insert(nodes[item.group_id], 'end', iid=f'r{index}', values=(
                media, Path(item.old_path).name, item.detected,
                Path(item.new_path).name if item.new_path != item.old_path else '—', shown_status), tags=(tag,))
        ready, review, conflicts, skipped_count = self._plan_counts(plan)
        self.status_var.set(
            f'{len(nodes)} 组 · {len(plan)} 个文件 · 可执行 {ready} · 待确认/填写 {review} · '
            f'冲突/错误 {conflicts} · 已跳过 {skipped_count}')
        if hasattr(self, 'preview_legend_var'):
            self.preview_legend_var.set(f'READY {ready}  ·  REVIEW {review}  ·  CONFLICT {conflicts}')
        self._sync_group_markers()
        self._sync_selection_markers()
        if plan:
            self._set_empty_state(visible=False)
        else:
            self._set_empty_state('没有发现可处理文件', '可以检查文件夹、子目录选项，或确认文件扩展名是否受支持。', visible=True)
        if any(x.status.startswith(('冲突', '错误')) for x in plan):
            self._set_chrome_state('CONFLICT DETECTED', 'error')
        elif review:
            self._set_chrome_state('CHECK BEFORE RUN', 'warning')
        elif ready:
            self._set_chrome_state('PREVIEW SAFE', 'success')
        else:
            self._set_chrome_state('NO READY ITEMS', 'neutral')

    def _plan_counts(self, plan=None):
        plan = self.plan if plan is None else plan
        ready = sum(x.status == READY for x in plan)
        review = sum(x.status.startswith('待') for x in plan)
        conflicts = sum(x.status.startswith(('冲突', '错误')) for x in plan)
        skipped = sum(x.status.startswith('已跳过') for x in plan)
        return ready, review, conflicts, skipped

    def update_run_state(self):
        ready, review, conflicts, _skipped = self._plan_counts()
        allowed = not self.busy and not self.dirty and ready > 0 and conflicts == 0
        self.run_btn.state(['!disabled'] if allowed else ['disabled'])
        if self.busy:
            self._set_chrome_state('PROCESSING...', 'busy')
        elif self.dirty:
            # settings_changed / operation_done already owns the more specific dirty-state message.
            return
        elif conflicts:
            self._set_chrome_state('CONFLICT DETECTED', 'error')
        elif review:
            # Ready items may still be executable, but the overall preview is not fully safe.
            self._set_chrome_state('CHECK BEFORE RUN', 'warning')
        elif ready:
            self._set_chrome_state('PREVIEW SAFE', 'success')
        else:
            self._set_chrome_state('NO READY ITEMS', 'neutral')

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
            self._alert('请刷新预览', '请先刷新预览，再编辑或跳过文件。', kind='warning')
            return False
        return bool(self.selected_indices())

    def show_detail(self, _event=None):
        indices = self.selected_indices()
        if indices and indices[0] < len(self.plan):
            item = self.plan[indices[0]]
            status = item.status if item.status else '未分类'
            source = str(item.old_path)
            target = str(item.new_path)
            self.detail_var.set(
                f'源：{source}  →  目标：{target}  ·  {status}  ·  {item.reason}  ·  SCORE {item.confidence}/100')
            if hasattr(self, 'detail_entry'):
                self.after_idle(lambda: self.detail_entry.xview_moveto(0))

    def copy_selected_detail(self):
        indices = self.selected_indices()
        if not indices or indices[0] >= len(self.plan):
            text = self.detail_var.get().strip()
            if not text:
                return
        else:
            item = self.plan[indices[0]]
            text = f'源文件：{item.old_path}\n目标文件：{item.new_path}'
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()
            self.status_var.set('已复制完整路径到剪贴板。')
        except tk.TclError:
            self.status_var.set('复制失败：系统剪贴板当前不可用。')

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
            self._alert('选择一个文件', '每次纠正一个文件；视频纠正后，关联字幕会一起更新。', kind='warning')
            return
        item = self.plan[indices[0]]
        value = self._prompt('纠正集数 / 特别篇',
            f'{Path(item.old_path).name}\n输入 03、12.5、SP01 或 NCOP02：',
            initial=self.overrides.get(item.old_path, item.detected if item.detected != '—' else ''))
        if value is not None:
            try:
                parse_override(value)
            except ValueError as exc:
                self._alert('输入有误', str(exc), kind='error')
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
            self._alert('无法执行', '请先解决或跳过冲突和错误。', kind='error')
            return
        count, review, conflicts, skipped = self._plan_counts()
        if not count:
            return
        other = max(0, len(self.plan) - count - review - conflicts - skipped)
        action = '原地重命名' if self.mode_var.get() == '原地重命名' else '复制整理（保留原文件）'
        summary = (
            f'{action}：可执行 {count} 个文件。\n'
            f'仍需确认/填写 {review} 个，已跳过 {skipped} 个'
            + (f'，其他不执行 {other} 个' if other else '')
            + '。\n待确认项目不会执行，按当前预览继续？')
        if self._confirm('确认执行', summary):
            plan = list(self.plan)
            self._start_task(lambda progress: execute_plan(plan, progress), self.operation_done)

    def operation_done(self, result):
        self.dirty = True
        self.status_var.set(result['message'])
        self._set_chrome_state('DONE' if result['ok'] else 'FAILED', 'success' if result['ok'] else 'error')
        self._alert('完成' if result['ok'] else '未完成', result['message'],
                    kind='success' if result['ok'] else 'error')
        if result['ok']:
            self.overrides.clear()
            self.skipped.clear()
        self.detail_var.set('文件状态已改变，请刷新预览。')
        self.after(50, self.check_recovery)

    def undo(self):
        if not self.busy and self._confirm('撤销上次操作',
                '改名操作将恢复原名；复制操作将删除本工具上次生成的副本，保留原文件。\n文件已改变时会停止撤销。继续？', kind='warning'):
            self._start_task(lambda _: undo_last(), self.operation_done)

    def recover(self):
        self._start_task(lambda _: recover_pending(), self.operation_done)

    def check_recovery(self):
        try:
            has_pending = bool(pending_operation())
            if has_pending:
                if hasattr(self, 'recover_btn') and not self.recover_btn.winfo_ismapped():
                    self.recover_btn.pack(side='right', padx=(0, 6), before=self.undo_btn)
                self.status_var.set('发现未完成的操作，请点击青色恢复按钮。')
                self._set_chrome_state('RECOVERY REQUIRED', 'warning')
            elif hasattr(self, 'recover_btn') and self.recover_btn.winfo_ismapped():
                self.recover_btn.pack_forget()
        except OSError as exc:
            self.status_var.set(f'恢复记录目录不可用：{exc}')

    def close(self):
        if self.busy:
            self._alert('正在处理', '请等待当前操作完成后关闭。', kind='warning')
        else:
            self.destroy()

    def destroy(self):
        self._stop_busy_animation()
        for callback in self.tk.splitlist(self.tk.call('after', 'info')):
            self.after_cancel(callback)
        super().destroy()


>>>>>>> Stashed changes
if __name__ == '__main__':
    App().mainloop()
