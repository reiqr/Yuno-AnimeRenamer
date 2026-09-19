import json
import os
import runpy
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import file_operations as ops
import renamer_core as core


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='anime_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.storage = self.root / 'history'
        self.patcher = patch.object(ops, '_storage', return_value=self.storage)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def file(self, name, content=None):
        p = self.source / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content if content is not None else name, encoding='utf-8')
        return p

    def plan(self, **kwargs):
        return core.build_plan(str(self.source), '作品', 1, '{title} - {episode:02d}', **kwargs)

    def snapshot(self):
        return {str(p.relative_to(self.source)): p.read_bytes()
                for p in self.source.rglob('*') if p.is_file()}

    def chain(self, cycle=False):
        a, b = self.file('A.mkv', 'alpha'), self.file('B.mkv', 'beta')
        c = a if cycle else self.source / 'C.mkv'
        return [core.RenameItem(str(s), str(d), '视频', '', 100, core.READY,
                               signature=tuple(ops.fingerprint(s))) for s, d in [(a, b), (b, c)]]


class DetectionTests(unittest.TestCase):
    def test_regular_and_technical(self):
        cases = {'Show S01E08.mkv': 8, 'Show E10.mkv': 10, 'Show E12.mkv': 12,
                 'Show 第24话.mkv': 24, '01.mkv': 1, '002.ass': 2, '04.chs.ass': 4,
                 '未来日记01.mkv': 1, 'MiraiNikki02.mkv': 2,
                 'Show [03] x265.mkv': 3, 'Show - 03 h264.mkv': 3,
                 'Show - 03 [1080].mkv': 3, 'Show [03] 5.1.mkv': 3,
                 'Show [03] AAC2.0.mkv': 3, 'Show - 03 1920x1080 10bit.mkv': 3,
                 'Show - 03 23.976fps.mkv': 3, 'Show.S01E03.1080p.mkv': 3,
                 '[2024] Show - 03.mkv': 3, 'Show E5.1.mkv': '5.1',
                 'Show - 12.5.mkv': '12.5', '12.5.mkv': '12.5', 'Show [12.5].mkv': '12.5'}
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(core.detect_episode(name).episode, expected)

    def test_specials_keep_indices(self):
        for kind in ('NCOP', 'NCED', 'SP', 'OVA', 'OAD', 'PV'):
            with self.subTest(kind=kind):
                d = core.detect_episode(f'Show {kind}02.mkv')
                self.assertEqual((d.special, d.special_index), (kind, 2))
                self.assertEqual(core.format_name('', '作品', 1, None, d.special, d.special_index), f'作品 - {kind}02')

    def test_multiepisode_needs_review(self):
        for name in ['Show - 01-02.mkv', 'Show S01E01-E02.mkv']:
            self.assertIsNone(core.detect_episode(name).episode)

    def test_fractional_template(self):
        self.assertEqual(core.format_name('{title} S{season:02d}E{episode:02d}', '作品', 2, '3.5'), '作品 S02E03.5')

    def test_invalid_names_templates_and_manual_input(self):
        for name in ['a/b', 'a\\b', 'CON', 'bad:', 'bad.', 'NUL.txt']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                core.validate_name(name)
        with self.assertRaises(ValueError):
            core.format_name('{typo}', '作品', 1, 3)
        for value in ['-1', 'abc', '../x', '10000']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                core.parse_override(value)


class PlanTests(Workspace):
    def test_groups_do_not_cross_directories(self):
        for folder in ['A', 'B']:
            self.file(f'{folder}/Show E03.mkv')
            self.file(f'{folder}/Show E03.chs.ass')
        initial = self.plan(recursive=True)
        settings = {x.group_id: core.GroupSettings(x.group, 2, 8 if x.group == 'B' else 1) for x in initial}
        plan = self.plan(recursive=True, force_sequence=True, group_settings=settings)
        for item in plan:
            self.assertEqual(item.episode, 8 if item.group == 'B' else 1)
            self.assertTrue(Path(item.new_path).name.startswith(item.group + ' - '))

    def test_explicit_seasons_form_separate_groups(self):
        self.file('Show S01E03.mkv')
        self.file('Show S02E03.mkv')
        self.file('Show S02E03.chs.ass')
        plan = self.plan(force_sequence=True)
        self.assertEqual(len({x.group_id for x in plan}), 2)
        self.assertTrue(all(x.episode == 1 for x in plan))

    def test_manual_video_correction_propagates(self):
        video = self.file('Show E03.mkv')
        self.file('Show E03.chs.ass')
        self.file('03.cht.ass')
        plan = self.plan(overrides={str(video): '12.5'})
        self.assertTrue(all(x.episode == '12.5' for x in plan))

    def test_forced_subtitle_ambiguous_blocks(self):
        self.file('First E03.mkv')
        self.file('Second E03.mkv')
        self.file('03.ass')
        sub = next(x for x in self.plan(force_sequence=True) if x.kind == '字幕')
        self.assertTrue(sub.status.startswith('待确认'))

    def test_skip_video_skips_linked_subtitle(self):
        video = self.file('Show E03.mkv')
        self.file('Show E03.ass')
        self.assertTrue(all(x.status.startswith('已跳过') for x in self.plan(skipped={str(video)})))

    def test_skip_resolves_collision_but_not_existing_file(self):
        a = self.file('A E03.mkv')
        self.file('B E03.mkv')
        self.assertTrue(all(x.status.startswith('冲突') for x in self.plan()))
        self.assertEqual(sum(x.status == core.READY for x in self.plan(skipped={str(a)})), 1)
        self.file('作品 - 03.mkv')
        self.assertTrue(any(x.status.startswith('冲突') for x in self.plan(skipped={str(a)})))

    def test_low_confidence_requires_confirmation(self):
        self.file('Show 3 name.mkv')
        self.assertTrue(self.plan()[0].status.startswith('待确认'))

    def test_copy_preserves_relative_layout(self):
        self.file('A/03.mkv')
        output = self.root / 'output'
        item = self.plan(recursive=True, mode='copy', output_folder=str(output))[0]
        self.assertEqual(Path(item.new_path), output / 'A' / '作品 - 03.mkv')
        with self.assertRaises(ValueError):
            self.plan(mode='copy', output_folder=str(self.source / 'output'))


class OperationTests(Workspace):
    def test_second_instance_cannot_recover_active_operation(self):
        with ops._operation_lock():
            result = ops.recover_pending()
        self.assertFalse(result['ok'])

    def test_chains_cycles_and_undo(self):
        for cycle in [False, True]:
            with self.subTest(cycle=cycle):
                plan = self.chain(cycle)
                before = self.snapshot()
                self.assertTrue(ops.execute_plan(plan)['ok'])
                self.assertTrue(ops.undo_last()['ok'])
                self.assertEqual(self.snapshot(), before)

    def test_failure_at_every_move_and_undo_step(self):
        for undo in [False, True]:
            for step in range(1, 5):
                with self.subTest(undo=undo, step=step):
                    for p in self.source.iterdir():
                        p.unlink()
                    plan = self.chain()
                    if undo:
                        self.assertTrue(ops.execute_plan(plan)['ok'])
                    before = self.snapshot()
                    move, calls = ops._move, [0]
                    def fail_once(src, dst):
                        calls[0] += 1
                        if calls[0] == step:
                            raise PermissionError('injected failure')
                        move(src, dst)
                    with patch.object(ops, '_move', side_effect=fail_once):
                        result = ops.undo_last() if undo else ops.execute_plan(plan)
                    self.assertFalse(result['ok'])
                    self.assertEqual(self.snapshot(), before)
                    self.assertFalse(ops.pending_operation())

    def test_journal_failure_changes_nothing(self):
        plan = self.chain()
        before = self.snapshot()
        with patch.object(ops, '_reserve_journal', side_effect=PermissionError('no journal')):
            self.assertFalse(ops.execute_plan(plan)['ok'])
        self.assertEqual(self.snapshot(), before)

    def test_history_failure_rolls_back(self):
        plan = self.chain()
        before = self.snapshot()
        with patch.object(ops, '_write_json', side_effect=OSError('disk full')):
            self.assertFalse(ops.execute_plan(plan)['ok'])
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(ops.pending_operation())

    def test_crash_recovered_from_disk(self):
        plan = self.chain()
        before = self.snapshot()
        move, calls = ops._move, [0]
        def crash(src, dst):
            calls[0] += 1
            if calls[0] == 4:
                raise SystemExit('simulated process death')
            move(src, dst)
        with patch.object(ops, '_move', side_effect=crash), self.assertRaises(SystemExit):
            ops.execute_plan(plan)
        self.assertTrue(ops.pending_operation())
        self.assertFalse(ops.execute_plan(plan)['ok'])
        self.assertTrue(ops.recover_pending()['ok'])
        self.assertEqual(self.snapshot(), before)

    def test_recovery_staging_failure_does_not_overwrite(self):
        plan = self.chain()
        before = self.snapshot()
        move, calls = ops._move, [0]
        def fail_twice(src, dst):
            calls[0] += 1
            if calls[0] in {4, 5}:
                raise PermissionError('locked')
            move(src, dst)
        with patch.object(ops, '_move', side_effect=fail_twice):
            self.assertFalse(ops.execute_plan(plan)['ok'])
        self.assertEqual(sorted(self.snapshot().values()), sorted(before.values()))
        self.assertTrue(ops.recover_pending()['ok'])
        self.assertEqual(self.snapshot(), before)

    def test_preview_changed_and_external_destination_blocked(self):
        self.file('03.mkv')
        plan = self.plan()
        self.file('03.mkv', 'changed')
        self.assertFalse(ops.execute_plan(plan)['ok'])
        plan = self.plan()
        target = Path(plan[0].new_path)
        target.write_text('unrelated')
        self.assertFalse(ops.execute_plan(plan)['ok'])
        self.assertEqual(target.read_text(), 'unrelated')

    def test_copy_and_undo_preserve_source(self):
        self.file('A/03.mkv')
        before = self.snapshot()
        plan = self.plan(recursive=True, mode='copy', output_folder=str(self.root / 'output'))
        self.assertTrue(ops.execute_plan(plan)['ok'])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(Path(plan[0].new_path).read_bytes(), Path(plan[0].old_path).read_bytes())
        self.assertTrue(ops.undo_last()['ok'])
        self.assertFalse(Path(plan[0].new_path).exists())
        self.assertEqual(self.snapshot(), before)

    def test_copy_undo_refuses_changed_copy(self):
        self.file('03.mkv')
        plan = self.plan(mode='copy', output_folder=str(self.root / 'output'))
        self.assertTrue(ops.execute_plan(plan)['ok'])
        Path(plan[0].new_path).write_text('edited after copy')
        self.assertFalse(ops.undo_last()['ok'])
        self.assertEqual(Path(plan[0].new_path).read_text(), 'edited after copy')

    def test_copy_failure_and_restart_cleanup(self):
        self.file('03.mkv')
        self.file('04.mkv')
        plan = self.plan(mode='copy', output_folder=str(self.root / 'output'))
        before = self.snapshot()
        move, calls = ops._move, [0]
        def crash(src, dst):
            calls[0] += 1
            if calls[0] == 2:
                raise SystemExit('crash')
            move(src, dst)
        with patch.object(ops, '_move', side_effect=crash), self.assertRaises(SystemExit):
            ops.execute_plan(plan)
        self.assertTrue(ops.recover_pending()['ok'])
        self.assertFalse(any(p.is_file() for p in (self.root / 'output').rglob('*')))
        self.assertEqual(self.snapshot(), before)

    def test_failed_operation_preserves_previous_undo(self):
        self.file('03.mkv')
        first = self.plan()
        self.assertTrue(ops.execute_plan(first)['ok'])
        self.file('04.mkv')
        second = self.plan()
        with patch.object(ops, '_write_json', side_effect=OSError('history failure')):
            self.assertFalse(ops.execute_plan(second)['ok'])
        self.assertTrue(ops.undo_last()['ok'])
        self.assertTrue((self.source / '03.mkv').exists())
        self.assertTrue((self.source / '04.mkv').exists())

    def test_copy_write_failure_cleans_partial_output(self):
        self.file('03.mkv', 'large enough data')
        plan = self.plan(mode='copy', output_folder=str(self.root / 'output'))
        def failed_copy(source, output, **kwargs):
            output.write(b'partial')
            raise OSError('disk full')
        with patch.object(ops.shutil, 'copyfileobj', side_effect=failed_copy):
            self.assertFalse(ops.execute_plan(plan)['ok'])
        self.assertFalse(any(p.is_file() for p in (self.root / 'output').rglob('*')))
        self.assertEqual((self.source / '03.mkv').read_text(), 'large enough data')

    def test_new_destination_during_publish_is_not_overwritten(self):
        self.file('03.mkv', 'original')
        plan = self.plan()
        move = ops._move
        target = Path(plan[0].new_path)
        def new_file(src, dst):
            if Path(dst) == target:
                target.write_text('unrelated')
            move(src, dst)
        with patch.object(ops, '_move', side_effect=new_file):
            self.assertFalse(ops.execute_plan(plan)['ok'])
        self.assertEqual(target.read_text(), 'unrelated')
        self.assertEqual((self.source / '03.mkv').read_text(), 'original')

    def test_pending_cleanup_failure_keeps_committed_result(self):
        plan = self.chain()
        unlink = Path.unlink
        pending, _ = ops._paths()
        def failed_unlink(path, *args, **kwargs):
            if path == pending:
                raise PermissionError('locked journal')
            return unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', failed_unlink):
            self.assertTrue(ops.execute_plan(plan)['ok'])
        self.assertTrue(ops.recover_pending()['ok'])
        self.assertEqual((self.source / 'B.mkv').read_text(), 'alpha')
        self.assertTrue(ops.undo_last()['ok'])


class GuiTests(Workspace):
    def setUp(self):
        super().setUp()
        module = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'AnimeRenamer.pyw'), run_name='test_ui')
        self.App = module['App']
        self.app = self.App()
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.dialogs = patch.multiple(module['messagebox'], showerror=Mock(), showinfo=Mock(), showwarning=Mock())
        self.dialogs.start()
        self.addCleanup(self.dialogs.stop)

    def wait(self):
        deadline = time.monotonic() + 6
        while self.app.busy and time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.01)
        self.assertFalse(self.app.busy, 'UI worker timed out')

    def scan(self):
        self.app.folder_var.set(str(self.source))
        self.app.title_var.set('作品')
        self.app.scan()
        self.wait()

    def test_settings_invalidate_execution(self):
        self.file('03.mkv')
        self.scan()
        self.assertFalse(self.app.run_btn.instate(['disabled']))
        self.app.title_var.set('新作品')
        self.assertTrue(self.app.run_btn.instate(['disabled']))
        self.assertTrue(self.app.dirty)

    def test_failed_scan_clears_previous_plan(self):
        self.file('03.mkv')
        self.scan()
        self.app.folder_var.set(str(self.root / 'missing'))
        self.app.scan()
        self.wait()
        self.assertEqual(self.app.plan, [])
        self.assertTrue(self.app.run_btn.instate(['disabled']))

    def test_skip_and_restore(self):
        self.file('03.mkv')
        self.scan()
        self.app.tree.selection_set('r0')
        self.app.toggle_skip()
        self.wait()
        self.assertEqual(self.app.plan[0].status, '已跳过')
        self.app.tree.selection_set('r0')
        self.app.toggle_skip()
        self.wait()
        self.assertEqual(self.app.plan[0].status, core.READY)

    def test_manual_edit_survives_refresh(self):
        video = self.file('03.mkv')
        self.scan()
        self.app.tree.selection_set('r0')
        g = self.App.edit_item.__globals__
        with patch.object(g['simpledialog'], 'askstring', return_value='12.5'):
            self.app.edit_item()
        self.wait()
        self.assertEqual(self.app.plan[0].episode, '12.5')
        self.app.scan()
        self.wait()
        self.assertEqual(self.app.overrides[str(video)], '12.5')

    def test_group_edit_updates_preview(self):
        self.file('03.mkv')
        self.scan()
        self.app.tree.selection_set('g0')
        with patch.dict(self.App.edit_group.__globals__, {'GroupDialog': Mock(return_value=SimpleNamespace(result=core.GroupSettings('另一部作品', 2, 5)))}):
            self.app.edit_group()
        self.wait()
        self.assertEqual(Path(self.app.plan[0].new_path).name, '另一部作品 - 03.mkv')

    def test_full_copy_execute_and_undo_ui(self):
        self.file('03.mkv')
        self.app.mode_var.set('复制整理（保留原文件）')
        self.app.output_var.set(str(self.root / 'output'))
        self.scan()
        target = Path(self.app.plan[0].new_path)
        with patch.object(self.App.execute.__globals__['messagebox'], 'askyesno', return_value=True):
            self.app.execute()
            self.wait()
            self.assertTrue(target.exists())
            self.assertTrue(self.app.run_btn.instate(['disabled']))
            self.app.undo()
            self.wait()
        self.assertFalse(target.exists())
        self.assertTrue((self.source / '03.mkv').exists())


if __name__ == '__main__':
    unittest.main()
