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
from ui_light_novel import LightNovelMixin
from ui_styles import StyleMixin
from ui_theme import ThemeMixin, ThemeToggle
from ui_view import ViewMixin


class App(LightNovelMixin, ThemeMixin, DialogMixin, StyleMixin, LayoutMixin, ViewMixin, ActionMixin, tk.Tk):
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


if __name__ == '__main__':
    App().mainloop()
