from __future__ import annotations

import queue
import threading
import tkinter as tk
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
        self.title(f'番剧批量重命名 · AnimeRenamer {VERSION}')
        self.geometry('1260x820')
        self.minsize(1050, 720)
        self.plan = []
        self.overrides, self.groups, self.skipped = {}, {}, set()
        self.busy, self.dirty = False, True
        self.source_context = ''
        self.group_nodes = {}
        self._build_ui()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(150, self.check_recovery)

    def _build_ui(self):
        style = ttk.Style(self)
        if 'vista' in style.theme_names():
            style.theme_use('vista')
        style.configure('Treeview', rowheight=29)
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='番剧批量重命名', font=('Microsoft YaHei UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(outer, text='离线识别 · 按目录和季号分组 · 确认预览后执行').pack(anchor='w', pady=(4, 12))
        form = ttk.LabelFrame(outer, text='文件与命名', padding=10)
        form.pack(fill='x')
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
        ttk.Label(form, text='输入文件夹').grid(row=0, column=0, sticky='w', padx=(0, 8))
        ttk.Entry(form, textvariable=self.folder_var).grid(row=0, column=1, columnspan=5, sticky='ew', pady=4)
        ttk.Button(form, text='选择…', command=self.choose_folder).grid(row=0, column=6, padx=8)
        ttk.Label(form, text='默认作品名').grid(row=1, column=0, sticky='w')
        ttk.Entry(form, textvariable=self.title_var, width=26).grid(row=1, column=1, sticky='ew', pady=4)
        ttk.Label(form, text='默认季度').grid(row=1, column=2, padx=8)
        ttk.Spinbox(form, from_=0, to=99, width=5, textvariable=self.season_var).grid(row=1, column=3)
        ttk.Label(form, text='命名规则').grid(row=1, column=4, padx=8)
        cb = ttk.Combobox(form, values=list(TEMPLATES), textvariable=self.template_name_var, state='readonly')
        cb.grid(row=1, column=5, sticky='ew')
        cb.bind('<<ComboboxSelected>>', self.on_template_change)
        ttk.Label(form, text='模板').grid(row=2, column=0, sticky='w')
        self.template_entry = ttk.Entry(form, textvariable=self.template_var, state='disabled')
        self.template_entry.grid(row=2, column=1, columnspan=5, sticky='ew', pady=4)
        ttk.Button(form, text='刷新预览', command=self.scan).grid(row=2, column=6, padx=8)
        ttk.Label(form, text='操作方式').grid(row=3, column=0, sticky='w')
        ttk.Combobox(form, textvariable=self.mode_var, state='readonly',
                     values=['原地重命名', '复制整理（保留原文件）']).grid(row=3, column=1, sticky='ew', pady=4)
        ttk.Label(form, text='复制到').grid(row=3, column=2, padx=8)
        self.output_entry = ttk.Entry(form, textvariable=self.output_var)
        self.output_entry.grid(row=3, column=3, columnspan=3, sticky='ew')
        ttk.Button(form, text='选择…', command=self.choose_output).grid(row=3, column=6, padx=8)
        opts = ttk.Frame(form)
        opts.grid(row=4, column=0, columnspan=7, sticky='w', pady=8)
        for text, variable in [('包含子文件夹', self.recursive_var), ('联动字幕', self.sub_var),
                               ('保留字幕语言', self.lang_var), ('每组全部正片按排序编号', self.force_var)]:
            ttk.Checkbutton(opts, text=text, variable=variable).pack(side='left', padx=(0, 12))
        ttk.Label(opts, text='起始集').pack(side='left')
        ttk.Spinbox(opts, from_=1, to=9999, textvariable=self.start_var, width=5).pack(side='left', padx=4)
        form.columnconfigure(1, weight=2)
        form.columnconfigure(5, weight=2)
        toolbar = ttk.Frame(outer)
        toolbar.pack(fill='x', pady=(12, 6))
        for label, callback in [('设置所选分组', self.edit_group), ('纠正集数 / 特别篇', self.edit_item),
                                ('跳过 / 恢复所选', self.toggle_skip), ('清除所选纠正', self.clear_override)]:
            ttk.Button(toolbar, text=label, command=callback).pack(side='left', padx=(0, 8))
        ttk.Label(toolbar, text='双击文件纠正；空格切换跳过', foreground='#666666').pack(side='right')
        preview = ttk.Frame(outer)
        preview.pack(fill='both', expand=True)
        cols = ('kind', 'old', 'detected', 'new', 'status')
        self.tree = ttk.Treeview(preview, columns=cols, show='tree headings', selectmode='extended')
        self.tree.heading('#0', text='分组')
        self.tree.column('#0', width=155, minwidth=100)
        for col, label, width in [('kind', '类型', 50), ('old', '原文件名', 255),
                                  ('detected', '集数 / 类型', 100), ('new', '目标文件名', 255),
                                  ('status', '状态', 220)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, minwidth=50)
        self.tree.tag_configure('warning', foreground='#9b4700')
        self.tree.tag_configure('error', foreground='#b00020')
        self.tree.tag_configure('skipped', foreground='#777777')
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
        self.detail_var = tk.StringVar(value='待确认的文件不会自动执行；请纠正集数或选择跳过。')
        ttk.Label(outer, textvariable=self.detail_var, wraplength=1150).pack(fill='x', pady=(8, 4))
        bottom = ttk.Frame(outer)
        bottom.pack(fill='x')
        self.status_var = tk.StringVar(value='选择文件夹，填写默认作品名或分别设置各组名称。')
        ttk.Label(outer, textvariable=self.status_var, wraplength=1150).pack(fill='x', pady=(8, 0))
        ttk.Button(bottom, text='恢复中断操作', command=self.recover).pack(side='left')
        ttk.Button(bottom, text='撤销上次操作', command=self.undo).pack(side='left', padx=8)
        self.run_btn = ttk.Button(bottom, text='执行预览中的操作', command=self.execute, state='disabled')
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
            tag = 'error' if status.startswith(('冲突', '错误')) else ('warning' if status.startswith(('待',)) else ('skipped' if status == '已跳过' else ''))
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
