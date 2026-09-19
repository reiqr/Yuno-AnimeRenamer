from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from renamer_core import build_plan, execute_plan, undo_last

APP_TITLE = '番剧批量重命名 AnimeRenamer v0.1.0'

TEMPLATES = {
    '番剧名 - 01': '{title} - {episode:02d}',
    '番剧名 S01E01': '{title} S{season:02d}E{episode:02d}',
    '番剧名 - E01': '{title} - E{episode:02d}',
    '[01] 番剧名': '[{episode:02d}] {title}',
    '自定义': '{title} - {episode:02d}',
}

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry('1180x720')
        self.minsize(980, 600)
        self.plan = []
        self._build_style()
        self._build_ui()

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use('vista')
        except tk.TclError:
            pass
        style.configure('Treeview', rowheight=27)
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 16, 'bold'))
        style.configure('Hint.TLabel', foreground='#666666')

    def _build_ui(self):
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill='both', expand=True)

        ttk.Label(outer, text='番剧批量重命名', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='先预览，再执行。不会修改视频内容，只修改文件名。', style='Hint.TLabel').pack(anchor='w', pady=(2, 12))

        form = ttk.LabelFrame(outer, text='重命名设置', padding=10)
        form.pack(fill='x')

        self.folder_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.season_var = tk.IntVar(value=1)
        self.template_name_var = tk.StringVar(value='番剧名 - 01')
        self.template_var = tk.StringVar(value=TEMPLATES['番剧名 - 01'])
        self.recursive_var = tk.BooleanVar(value=False)
        self.sub_var = tk.BooleanVar(value=True)
        self.lang_var = tk.BooleanVar(value=True)
        self.force_var = tk.BooleanVar(value=False)
        self.start_var = tk.IntVar(value=1)

        ttk.Label(form, text='文件夹').grid(row=0, column=0, sticky='w', padx=(0, 8), pady=5)
        ttk.Entry(form, textvariable=self.folder_var).grid(row=0, column=1, columnspan=5, sticky='ew', pady=5)
        ttk.Button(form, text='选择…', command=self.choose_folder).grid(row=0, column=6, padx=(8, 0), pady=5)

        ttk.Label(form, text='番剧名称').grid(row=1, column=0, sticky='w', padx=(0, 8), pady=5)
        ttk.Entry(form, textvariable=self.title_var, width=28).grid(row=1, column=1, sticky='ew', pady=5)
        ttk.Label(form, text='季度').grid(row=1, column=2, sticky='e', padx=(12, 6))
        ttk.Spinbox(form, from_=1, to=99, textvariable=self.season_var, width=5).grid(row=1, column=3, sticky='w')
        ttk.Label(form, text='命名规则').grid(row=1, column=4, sticky='e', padx=(12, 6))
        cb = ttk.Combobox(form, textvariable=self.template_name_var, values=list(TEMPLATES), state='readonly', width=18)
        cb.grid(row=1, column=5, sticky='ew')
        cb.bind('<<ComboboxSelected>>', self.on_template_change)

        ttk.Label(form, text='模板').grid(row=2, column=0, sticky='w', padx=(0, 8), pady=5)
        self.template_entry = ttk.Entry(form, textvariable=self.template_var)
        self.template_entry.grid(row=2, column=1, columnspan=5, sticky='ew', pady=5)
        ttk.Button(form, text='预览', command=self.scan).grid(row=2, column=6, padx=(8, 0), pady=5)

        opts = ttk.Frame(form)
        opts.grid(row=3, column=0, columnspan=7, sticky='w', pady=(7, 2))
        ttk.Checkbutton(opts, text='包含子文件夹', variable=self.recursive_var).pack(side='left', padx=(0, 14))
        ttk.Checkbutton(opts, text='同时重命名字幕', variable=self.sub_var).pack(side='left', padx=(0, 14))
        ttk.Checkbutton(opts, text='保留字幕语言标签', variable=self.lang_var).pack(side='left', padx=(0, 14))
        ttk.Checkbutton(opts, text='无法识别时按排序强制编号', variable=self.force_var).pack(side='left', padx=(0, 6))
        ttk.Label(opts, text='起始集').pack(side='left')
        ttk.Spinbox(opts, from_=1, to=999, textvariable=self.start_var, width=5).pack(side='left', padx=(4, 0))

        form.columnconfigure(1, weight=2)
        form.columnconfigure(5, weight=1)

        preview = ttk.LabelFrame(outer, text='重命名预览', padding=8)
        preview.pack(fill='both', expand=True, pady=(12, 0))

        cols = ('kind', 'old', 'detected', 'confidence', 'new', 'status')
        self.tree = ttk.Treeview(preview, columns=cols, show='headings', selectmode='browse')
        headings = {'kind':'类型','old':'原文件名','detected':'识别','confidence':'置信度','new':'新文件名','status':'状态'}
        widths = {'kind':60,'old':360,'detected':110,'confidence':75,'new':320,'status':170}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor='w' if c not in {'confidence','kind'} else 'center')
        ybar = ttk.Scrollbar(preview, orient='vertical', command=self.tree.yview)
        xbar = ttk.Scrollbar(preview, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        ybar.grid(row=0, column=1, sticky='ns')
        xbar.grid(row=1, column=0, sticky='ew')
        preview.rowconfigure(0, weight=1)
        preview.columnconfigure(0, weight=1)

        bottom = ttk.Frame(outer)
        bottom.pack(fill='x', pady=(10, 0))
        self.status_var = tk.StringVar(value='请选择一个番剧文件夹。')
        ttk.Label(bottom, textvariable=self.status_var, style='Hint.TLabel').pack(side='left', fill='x', expand=True)
        ttk.Button(bottom, text='撤销上次重命名', command=self.undo).pack(side='right', padx=(8, 0))
        self.run_btn = ttk.Button(bottom, text='执行重命名', command=self.execute)
        self.run_btn.pack(side='right')

    def choose_folder(self):
        folder = filedialog.askdirectory(title='选择番剧文件夹')
        if not folder:
            return
        self.folder_var.set(folder)
        if not self.title_var.get().strip():
            self.title_var.set(Path(folder).name)
        self.scan()

    def on_template_change(self, _event=None):
        name = self.template_name_var.get()
        self.template_var.set(TEMPLATES.get(name, self.template_var.get()))
        if name != '自定义':
            self.template_entry.state(['disabled'])
        else:
            self.template_entry.state(['!disabled'])

    def scan(self):
        folder = self.folder_var.get().strip()
        title = self.title_var.get().strip()
        if not folder or not Path(folder).is_dir():
            messagebox.showwarning('提示', '请先选择有效的番剧文件夹。')
            return
        if not title:
            messagebox.showwarning('提示', '请输入番剧名称。')
            return

        try:
            self.plan = build_plan(
                folder=folder,
                title=title,
                season=max(1, int(self.season_var.get())),
                template=self.template_var.get().strip() or '{title} - {episode:02d}',
                recursive=self.recursive_var.get(),
                rename_subtitles=self.sub_var.get(),
                preserve_language=self.lang_var.get(),
                force_sequence=self.force_var.get(),
                sequence_start=max(1, int(self.start_var.get())),
            )
        except Exception as e:
            messagebox.showerror('扫描失败', str(e))
            return

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        counts = {'可重命名':0, '无需修改':0, '冲突':0, '未识别':0}
        for i, item in enumerate(self.plan):
            old = Path(item.old_path).name
            new = Path(item.new_path).name
            conf = f'{item.confidence}%' if item.confidence else '-'
            self.tree.insert('', 'end', iid=str(i), values=(item.kind, old, item.detected, conf, new, item.status))
            if item.status == '可重命名': counts['可重命名'] += 1
            elif item.status == '无需修改': counts['无需修改'] += 1
            elif item.status.startswith('冲突'): counts['冲突'] += 1
            else: counts['未识别'] += 1

        self.status_var.set(
            f"共 {len(self.plan)} 个文件：可重命名 {counts['可重命名']}，无需修改 {counts['无需修改']}，"
            f"冲突 {counts['冲突']}，未识别 {counts['未识别']}。"
        )

    def execute(self):
        if not self.plan:
            self.scan()
            if not self.plan:
                return
        conflicts = [x for x in self.plan if x.status.startswith('冲突')]
        if conflicts:
            messagebox.showerror('存在冲突', '预览中存在目标文件名冲突。请先调整命名规则或文件内容。')
            return
        count = sum(x.status == '可重命名' for x in self.plan)
        if count == 0:
            messagebox.showinfo('提示', '当前没有需要重命名的文件。')
            return
        if not messagebox.askyesno('确认执行', f'将重命名 {count} 个文件。\n\n建议首次使用先复制一小部分文件测试。\n是否继续？'):
            return
        result = execute_plan(self.plan)
        if result['ok']:
            messagebox.showinfo('完成', result['message'])
            self.scan()
        else:
            messagebox.showerror('失败', result['message'])

    def undo(self):
        if not messagebox.askyesno('确认撤销', '将尝试恢复上一次由 AnimeRenamer 执行的重命名。是否继续？'):
            return
        result = undo_last()
        if result['ok']:
            messagebox.showinfo('已撤销', result['message'])
            if self.folder_var.get().strip():
                self.scan()
        else:
            messagebox.showerror('无法撤销', result['message'])

if __name__ == '__main__':
    App().mainloop()
