import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from renamer_core import GroupSettings

class GroupDialog(simpledialog.Dialog):
    def __init__(self, parent, label, settings):
        self.settings = settings
        super().__init__(parent, '设置分组：' + label)

    def body(self, master):
        # Match the main Future Diary theme instead of falling back to classic Tk styling.
        colors = getattr(self.parent, 'COLORS', {})
        self.configure(bg=colors.get('bg', '#0D0B11'))
        master.configure(bg=colors.get('panel', '#141119'))
        ttk.Label(master, text='GROUP SETTINGS  /  分组规则', style='Section.TLabel').grid(
            row=0, column=0, columnspan=2, sticky='w', padx=12, pady=(12, 2))
        ttk.Label(master, text='留空则使用主界面的默认设置。', style='MutedPanel.TLabel').grid(
            row=1, column=0, columnspan=2, sticky='w', padx=12, pady=(0, 10))
        self.fields = []
        for row, (label, value) in enumerate([
            ('作品名称', self.settings.title), ('季度（0–99）', self.settings.season),
            ('排序起始集（1–9999）', self.settings.start)], 2):
            ttk.Label(master, text=label, style='MutedPanel.TLabel').grid(
                row=row, column=0, sticky='w', padx=(12, 10), pady=6)
            entry = ttk.Entry(master, width=32)
            entry.insert(0, '' if value is None else str(value))
            entry.grid(row=row, column=1, sticky='ew', padx=(0, 12), pady=6)
            self.fields.append(entry)
        master.columnconfigure(1, weight=1)
        return self.fields[0]

    def buttonbox(self):
        box = ttk.Frame(self, style='Panel.TFrame', padding=(12, 10))
        ttk.Button(box, text='保存设置', width=12, command=self.ok,
                   style='Primary.TButton', default='active').pack(side='right', padx=(8, 0))
        ttk.Button(box, text='取消', width=10, command=self.cancel,
                   style='Ghost.TButton').pack(side='right')
        self.bind('<Return>', self.ok)
        self.bind('<Escape>', self.cancel)
        box.pack(fill='x')

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
            if hasattr(self.parent, '_alert'):
                self.parent._alert('输入有误', str(exc), kind='error')
            else:
                self._alert('输入有误', str(exc), kind='error')
            return False
        self.result = GroupSettings(title, season, start)
        return True


class DialogMixin:
    def _legacy_dialog_mode(self):
        # The bundled GUI tests monkey-patch tkinter dialogs. Keep that path intact.
        return bool(getattr(self, '_test_dialog_mode', False))

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
