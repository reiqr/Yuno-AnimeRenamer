from pathlib import Path
import sys
import tkinter as tk
import tkinter.font as tkfont

class ThemeToggle(tk.Checkbutton):
    """Pill-like Boolean toggle that also exposes ttk-style state() for busy locking."""
    def __init__(self, master, *, text, variable, colors, font):
        self._colors = colors
        super().__init__(
            master, text=text, variable=variable, indicatoron=False,
            relief='flat', bd=0, highlightthickness=1, padx=11, pady=5,
            anchor='center', cursor='hand2', font=font,
            bg=colors['off_bg'], fg=colors['off_fg'],
            activebackground=colors['hover_bg'], activeforeground=colors['on_fg'],
            selectcolor=colors['on_bg'],
            highlightbackground=colors['border'], highlightcolor=colors['accent'],
            disabledforeground=colors['disabled_fg'],
        )
        variable.trace_add('write', self._sync_visual)
        self.bind('<Enter>', self._enter, add='+')
        self.bind('<Leave>', self._leave, add='+')
        self.bind('<ButtonPress-1>', self._press, add='+')
        self.bind('<ButtonRelease-1>', self._release, add='+')
        self._sync_visual()

    def _selected(self):
        try:
            variable = self.cget('variable')
            if not variable:
                return False
            return bool(self.tk.getboolean(self.getvar(variable)))
        except (tk.TclError, ValueError):
            return False

    def _sync_visual(self, *_):
        if str(self.cget('state')) == 'disabled':
            return
        selected = self._selected()
        bg = self._colors['on_bg'] if selected else self._colors['off_bg']
        self.configure(
            bg=bg,
            selectcolor=bg,
            fg=self._colors['on_fg'] if selected else self._colors['off_fg'],
            highlightbackground=self._colors['accent'] if selected else self._colors['border'],
        )

    def _enter(self, _event=None):
        if str(self.cget('state')) != 'disabled':
            self.configure(bg=self._colors['on_bg'] if self._selected() else self._colors['hover_bg'])

    def _leave(self, _event=None):
        self._sync_visual()

    def _press(self, _event=None):
        if str(self.cget('state')) != 'disabled':
            self.configure(bg=self._colors.get('press_bg', self._colors['hover_bg']))

    def _release(self, _event=None):
        if str(self.cget('state')) != 'disabled':
            # Tk updates the Checkbutton variable in its class binding. Sync on idle so
            # the final off/on state always wins after a repeated click.
            self.after_idle(self._sync_visual)

    def state(self, spec=None):
        current = ('disabled',) if str(self.cget('state')) == 'disabled' else ()
        if spec is None:
            return current
        for token in spec:
            if token == 'disabled':
                self.configure(state='disabled', cursor='arrow', bg=self._colors['disabled_bg'])
            elif token == '!disabled':
                self.configure(state='normal', cursor='hand2')
                self._sync_visual()
        return current


class ThemeMixin:
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
            module_dir = Path(__file__).resolve().parent
            roots.append(module_dir)
            # Source layout keeps UI modules in ./ui while assets stay at repository root.
            roots.append(module_dir.parent)
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

    def _set_banner_variant(self, variant='dark'):
        variant = 'bright' if variant == 'bright' else 'dark'
        if getattr(self, '_banner_variant', 'dark') != variant:
            self._banner_variant = variant
            self._draw_banner()

    def _draw_banner(self, _event=None):
        canvas = getattr(self, 'banner_canvas', None)
        if not canvas:
            return
        canvas.delete('overlay')
        width = max(canvas.winfo_width(), 720)
        variant = getattr(self, '_banner_variant', 'dark')
        if variant == 'bright':
            # Ready/success states use the dedicated bright material with only a light
            # readability veil behind the right-side copy.
            banner = getattr(self, 'banner_bright_photo_wide', None) if width >= 840 else getattr(self, 'banner_bright_photo', None)
            veil_fill, veil_stipple = '#150B13', 'gray25'
        else:
            # Waiting/dirty/review/error states use the dedicated dark material.  The
            # additional veil is intentionally stronger so a dark state can never read
            # as the bright banner even when the two source images are close in exposure.
            banner = getattr(self, 'banner_dark_photo_wide', None) if width >= 840 else getattr(self, 'banner_dark_photo', None)
            veil_fill, veil_stipple = '#050406', 'gray75'
        if banner:
            canvas.create_image(0, 0, image=banner, anchor='nw', tags='overlay')
        height = max(82, canvas.winfo_height())
        if variant == 'dark':
            canvas.create_rectangle(0, 0, width, height, fill='#050406', stipple='gray50',
                                    outline='', tags='overlay')
        # Keep an additional readability veil behind the right-side title copy.
        canvas.create_rectangle(max(420, int(width * 0.52)), 0, width, height,
                                fill=veil_fill, stipple=veil_stipple, outline='', tags='overlay')
        tx = max(470, int(width * 0.58))
        title_fill = '#FFF5F9' if variant == 'bright' else '#CFC3CA'
        subtitle_fill = '#FF79AE' if variant == 'bright' else '#B84D76'
        step_fill = '#D8CFD4' if variant == 'bright' else '#8E838B'
        canvas.create_text(tx, 17, text='ANIME RENAMER', anchor='w', fill=title_fill,
                           font=(self.FONTS['latin'], 17, 'bold'), tags='overlay')
        canvas.create_text(tx, 37, text='未来日记 · RENAME TERMINAL', anchor='w', fill=subtitle_fill,
                           font=(self.FONTS['body'], 9, 'bold'), tags='overlay')
        canvas.create_text(tx, 56, text='01 SCAN   →   02 CHECK   →   03 REWRITE', anchor='w', fill=step_fill,
                           font=(self.FONTS['mono'], 7, 'bold'), tags='overlay')
        line_y = min(height - 8, 70)
        canvas.create_line(tx, line_y, min(width - 24, tx + 170), line_y,
                           fill='#FF4F91' if variant == 'bright' else '#8B3154', width=2, tags='overlay')
        canvas.create_line(min(width - 24, tx + 170), line_y, min(width - 24, tx + 280), line_y,
                           fill='#38D6D0' if variant == 'bright' else '#245F60', width=2, tags='overlay')
        canvas.create_rectangle(0, height - 3, width, height, fill='#0A080D', outline='', tags='overlay')
        canvas.create_line(0, height - 3, min(width, int(width * 0.38)), height - 3, fill='#8C2B59', width=1, tags='overlay')
        canvas.create_line(max(0, int(width * 0.72)), height - 3, width, height - 3, fill='#245A5A', width=1, tags='overlay')
