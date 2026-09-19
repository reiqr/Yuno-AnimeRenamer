import tkinter as tk


class ViewMixin:
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
        """Fill the preview viewport exactly while respecting useful minimums."""
        if not hasattr(self, 'tree'):
            return
        specs = [
            ('#0', 0.12, 80), ('kind', 0.06, 46), ('old', 0.29, 155),
            ('detected', 0.10, 72), ('new', 0.29, 155), ('status', 0.14, 95),
        ]
        minimum_total = sum(minimum for _col, _ratio, minimum in specs)
        width = max(minimum_total, self.tree.winfo_width() - 2)
        widths = {col: max(minimum, int(width * ratio))
                  for col, ratio, minimum in specs}

        # Min-width clamping can make the sum wider than the viewport on compact
        # windows.  Trim the high-flex columns first; otherwise give rounding slack
        # to TARGET so there is no unexplained gutter beside STATE/scrollbar.
        delta = width - sum(widths.values())
        if delta < 0:
            overflow = -delta
            minimums = {col: minimum for col, _ratio, minimum in specs}
            for col in ('old', 'new', 'status', '#0', 'detected', 'kind'):
                reducible = max(0, widths[col] - minimums[col])
                take = min(reducible, overflow)
                widths[col] -= take
                overflow -= take
                if overflow == 0:
                    break
        elif delta > 0:
            widths['new'] += delta

        for col, _ratio, minimum in specs:
            try:
                self.tree.column(col, width=widths[col], minwidth=minimum)
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
            novel = hasattr(self, 'content_type_var') and self.content_type_var.get() == '轻小说'
            hint = '作品名或起始卷' if novel else '作品名、季度或起始集'
            self.detail_var.set(f'分组行 · 单击可选择整组，使用 GROUP 按钮设置该组的{hint}。')

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
            novel = hasattr(self, 'content_type_var') and self.content_type_var.get() == '轻小说'
            self.detail_var.set('待确认的文件不会执行；悬停查看依据，双击可纠正卷数。' if novel
                                else '待确认的文件不会执行；悬停查看依据，双击可纠正集数。')

    def _set_empty_state(self, title=None, subtitle=None, visible=True):
        if not hasattr(self, 'empty_state'):
            return
        if title is not None:
            self.empty_title_var.set(title)
        if subtitle is not None:
            self.empty_sub_var.set(subtitle)
        if visible:
            width = getattr(self, 'empty_state_width', 390)
            height = getattr(self, 'empty_state_height', 116)
            self.empty_state.place(relx=0.5, rely=0.50, anchor='center', width=width, height=height)
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
        if hasattr(self, '_set_banner_variant'):
            # Safe preview / successful completion use the bright material.
            # Waiting, dirty, review and error states stay on the darker material.
            if mode == 'success':
                self._set_banner_variant('bright')
            elif mode != 'busy':
                self._set_banner_variant('dark')

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
        self._set_banner_variant('bright' if (self._busy_anim_step % 2) else 'dark')
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
