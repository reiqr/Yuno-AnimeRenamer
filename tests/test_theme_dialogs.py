import runpy
import unittest
from pathlib import Path
import tkinter as tk


class ThemeDialogTests(unittest.TestCase):
    def setUp(self):
        module = runpy.run_path(
            str(Path(__file__).resolve().parents[1] / 'AnimeRenamer.pyw'),
            run_name='theme_dialog_test')
        self.app = module['App']()
        self.app.withdraw()
        self.app._test_dialog_mode = False
        self.addCleanup(self.app.destroy)

    def _walk(self, widget):
        for child in widget.winfo_children():
            yield child
            yield from self._walk(child)

    def _top(self):
        tops = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertTrue(tops, 'theme modal did not create a Toplevel')
        return tops[-1]

    def _invoke(self, text):
        top = self._top()
        button = next((w for w in self._walk(top)
                       if isinstance(w, tk.Button) and w.cget('text') == text), None)
        self.assertIsNotNone(button, f'button not found: {text}')
        button.invoke()

    def test_confirm_and_cancel_buttons(self):
        self.app.after(50, lambda: self._invoke('继续执行'))
        self.assertTrue(self.app._confirm('测试', '确认继续？'))
        self.app.after(50, lambda: self._invoke('取消'))
        self.assertFalse(self.app._confirm('测试', '确认继续？'))

    def test_prompt_accepts_input(self):
        def fill_and_accept():
            top = self._top()
            entry = next(w for w in self._walk(top) if isinstance(w, tk.Entry))
            entry.delete(0, 'end')
            entry.insert(0, '12.5')
            self._invoke('确认')
        self.app.after(50, fill_and_accept)
        self.assertEqual(self.app._prompt('输入', '请输入：', initial='03'), '12.5')

    def test_keyboard_escape_and_return(self):
        self.app.after(80, lambda: (self._top().focus_force(), self._top().event_generate('<Escape>', when='tail')))
        self.assertFalse(self.app._confirm('测试', 'Esc 取消？'))

        def fill_and_return():
            top = self._top()
            entry = next(w for w in self._walk(top) if isinstance(w, tk.Entry))
            entry.delete(0, 'end')
            entry.insert(0, 'SP01')
            top.focus_force()
            top.event_generate('<Return>', when='tail')
        self.app.after(50, fill_and_return)
        self.assertEqual(self.app._prompt('输入', 'Enter 确认：'), 'SP01')


if __name__ == '__main__':
    unittest.main()
