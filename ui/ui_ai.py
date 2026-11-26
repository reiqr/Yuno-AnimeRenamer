from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from urllib.parse import urlsplit

import ai_analysis as ai


class AISettingsDialog(simpledialog.Dialog):
    def __init__(self, parent, settings, key):
        self.settings = settings
        self.key = key
        super().__init__(parent, 'AI 接口设置')

    def body(self, master):
        default = self.settings.get('provider', 'OpenAI')
        self.provider = tk.StringVar(value=default if default in ai.PROVIDERS else 'OpenAI')
        self.base = tk.StringVar(value=self.settings.get('base_url', ai.PROVIDERS[self.provider.get()][0]))
        self.model = tk.StringVar(value=self.settings.get('model', ''))
        self.token = tk.StringVar(value=self.key)
        ttk.Label(master, text='服务商').grid(row=0, column=0, sticky='w', padx=8, pady=5)
        combo = ttk.Combobox(master, textvariable=self.provider, values=list(ai.PROVIDERS), state='readonly')
        combo.grid(row=0, column=1, sticky='ew', padx=8)
        combo.bind('<<ComboboxSelected>>', self.change_provider)
        for row, (label, variable) in enumerate([
            ('接口地址', self.base), ('模型 ID', self.model), ('API 密钥', self.token)
        ], 1):
            ttk.Label(master, text=label).grid(row=row, column=0, sticky='w', padx=8, pady=5)
            ttk.Entry(master, textvariable=variable, width=58,
                      show='*' if variable is self.token else '').grid(row=row, column=1, sticky='ew', padx=8)
        ttk.Label(master, text='密钥只在本次运行中保留。留空可读取对应环境变量；本机 Ollama 通常不需要密钥。',
                  wraplength=420).grid(row=4, columnspan=2, sticky='w', padx=8, pady=8)
        # Re-enter the secret if its destination changes.
        self.base.trace_add('write', lambda *_: self.token.set(''))
        return combo

    def change_provider(self, _event):
        self.base.set(ai.PROVIDERS[self.provider.get()][0])
        self.model.set('')

    def validate(self):
        settings = dict(provider=self.provider.get(), base_url=self.base.get().strip(),
                        model=self.model.get().strip())
        try:
            ai.endpoint(settings)
            ai.save_settings(settings)
        except (ValueError, OSError) as exc:
            messagebox.showerror('无法保存 AI 设置', str(exc), parent=self)
            return False
        self.result = settings, self.token.get().strip()
        return True


class AIMixin:
    _ai_key = ''
    _ai_key_endpoint = None

    def configure_ai(self):
        if self.busy:
            return
        try:
            settings = ai.load_settings()
        except (ValueError, OSError):
            settings = {}
            self._alert('AI 设置', '无法读取之前的设置，请重新填写。', kind='warning')
        try:
            key = self._ai_key if ai.endpoint(settings) == self._ai_key_endpoint else ''
        except ValueError:
            key = ''
        result = AISettingsDialog(self, settings, key).result
        if result is not None:
            saved, self._ai_key = result
            self._ai_key_endpoint = ai.endpoint(saved)

    def analyze_selection(self):
        if self.busy:
            return
        if self.content_type_var.get() == '轻小说':
            self._alert('AI 分析', '当前 AI 分析支持番剧集数和特别篇。', kind='info')
            return
        if not self.can_edit():
            if not self.dirty:
                self._alert('AI 分析', '请在预览中选中要分析的文件。', kind='info')
            return
        items = [self.plan[i] for i in self.selected_indices()
                 if not self.plan[i].status.startswith('已跳过')]
        if not 1 <= len(items) <= ai.MAX_FILES:
            self._alert('AI 分析', f'每次请选择 1 至 {ai.MAX_FILES} 个未跳过的文件。', kind='warning')
            return
        try:
            settings = ai.load_settings()
            url = ai.endpoint(settings)
            host = urlsplit(url).netloc
        except (ValueError, OSError):
            self._alert('AI 分析', '请先打开「设置 → AI 接口设置」，填写并保存接口和模型。', kind='warning')
            return
        if not self._confirm('发送文件名进行 AI 分析',
                             f'将向 {host} 发送 {len(items)} 个文件名。'
                             '\n文件内容和完整路径不会发送。继续？'):
            return
        filenames = [Path(item.old_path).name for item in items]
        key = self._ai_key if url == self._ai_key_endpoint else ''

        def completed(suggestions):
            if not suggestions:
                self._alert('AI 分析', '本次没有得到可用的集数建议。', kind='info')
                return
            rows = [f'{filenames[i][:52]} → {value}' for i, value in suggestions.items()]
            if self._confirm('应用 AI 建议到预览', '\n'.join(rows) + '\n\n应用后请核对预览。'):
                # Queue after the current worker has restored its widget states.
                self.overrides.update({items[i].old_path: value for i, value in suggestions.items()})
                self.after_idle(self.scan)

        self.status_var.set('正在请求 AI 分析…')
        self._start_task(lambda _: ai.analyze_filenames(settings, filenames, key), completed)
