import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from renamer_core import (READY, GroupSettings, build_plan, parse_override, execute_plan,
                          undo_last, recover_pending, pending_operation)
from ui_constants import TEMPLATES
from ui_dialogs import GroupDialog
from ui_theme import ThemeToggle

def _format_bytes(value):
    value = float(max(0, value or 0))
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f'{value:.0f} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024


def _format_speed(value):
    return f'{_format_bytes(value)}/s'


class ActionMixin:
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

    def _start_task(self, function, completed, cancellable=False):
        if self.busy:
            return
        self.busy = True
        self._cancel_event = threading.Event() if cancellable else None
        self._start_busy_animation()
        states = [(w, w.state()) for w in self._controls(self)]
        for widget, _ in states:
            widget.state(['disabled'])
        if cancellable and hasattr(self, 'transfer_frame'):
            self.transfer_progress_var.set(0.0)
            self.transfer_title_var.set('COPY  0.0%')
            self.transfer_detail_var.set('准备复制…')
            self.transfer_frame.pack(fill='x', pady=(0, 5), after=self.toolbar)
            self.cancel_copy_btn.state(['!disabled'])
        events = queue.Queue()

        def worker():
            try:
                events.put(('done', function(lambda *p: events.put(('progress', p)))))
            except Exception as exc:
                events.put(('error', str(exc)))

        def handle_progress(result):
            if len(result) >= 8:
                current, total, name, copied, total_bytes, file_copied, file_size, speed = result[:8]
                percent = 100.0 if total_bytes <= 0 else min(100.0, copied * 100.0 / total_bytes)
                self.transfer_progress_var.set(percent)
                self.transfer_title_var.set(
                    f'COPY  {percent:5.1f}%  ·  {_format_bytes(copied)} / {_format_bytes(total_bytes)}')
                self.transfer_detail_var.set(
                    f'{current}/{total} · {name} · {_format_bytes(file_copied)} / {_format_bytes(file_size)} · {_format_speed(speed)}')
                self.status_var.set(f'复制中 {percent:.1f}%：{name} · {_format_speed(speed)}')
            else:
                self.status_var.set(f'处理中 {result[0]}/{result[1]}：{result[2]}')

        def poll():
            try:
                while True:
                    kind, result = events.get_nowait()
                    if kind == 'progress':
                        handle_progress(result)
                        continue
                    self.busy = False
                    self._stop_busy_animation()
                    for widget, state in states:
                        widget.state(['!disabled'])
                        widget.state(state)
                    if hasattr(self, 'transfer_frame') and self.transfer_frame.winfo_manager():
                        self.transfer_frame.pack_forget()
                    self._cancel_event = None
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

    def cancel_current_copy(self):
        event = getattr(self, '_cancel_event', None)
        if not self.busy or event is None or event.is_set():
            return
        event.set()
        if hasattr(self, 'cancel_copy_btn'):
            self.cancel_copy_btn.state(['disabled'])
        if hasattr(self, 'transfer_title_var'):
            self.transfer_title_var.set('CANCELLING · 正在安全停止')
            self.transfer_detail_var.set('正在清理本次临时文件和已生成副本，请稍候…')
        self._stop_busy_animation()
        self._set_chrome_state('CANCELLING...', 'warning')

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
            copy_mode = self.mode_var.get() != '原地重命名'
            self._start_task(
                lambda progress: execute_plan(plan, progress, self._cancel_event),
                self.operation_done, cancellable=copy_mode)

    def operation_done(self, result):
        cancelled = bool(result.get('cancelled'))
        recovery_required = bool(result.get('recovery_required'))
        if cancelled and not recovery_required:
            self.dirty = False
            self.status_var.set(result['message'])
            self._set_chrome_state('CANCELLED', 'warning')
            self._alert('已取消', result['message'], kind='warning')
            self.detail_var.set('复制已安全取消；当前预览仍可继续使用。')
            self.after(50, self.check_recovery)
            return
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
