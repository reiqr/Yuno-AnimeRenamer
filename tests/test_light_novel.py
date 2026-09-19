import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import runpy

import file_operations as ops
from renamer_core import READY
from ui_light_novel import NOVEL_TEMPLATES, build_novel_plan, detect_book, parse_book_override


class LightNovelDetectionTests(unittest.TestCase):
    def test_common_volume_formats(self):
        cases = [
            ('无职转生 第1卷.epub', '无职转生', 1),
            ('[台版] 无职转生 02.epub', '无职转生', 2),
            ('Re Zero Vol.12.azw3', 'Re Zero', 12),
            ('狼与香辛料 v03.pdf', '狼与香辛料', 3),
            ('86―不存在的战区―Ep.4.epub', '86―不存在的战区―', 4),
        ]
        for filename, title, expected in cases:
            with self.subTest(filename=filename):
                self.assertEqual(detect_book(filename, title).volume, expected)

    def test_volume_title_and_part_are_preserved(self):
        d = detect_book('十二国记 1 月之影 影之海.epub', '十二国记')
        self.assertEqual((d.volume, d.volume_title, d.part), (1, '月之影 影之海', ''))
        d = detect_book('某作品 第7卷 上.epub', '某作品')
        self.assertEqual((d.volume, d.volume_title, d.part), (7, '', '上'))

    def test_digits_inside_title_are_not_volume(self):
        d = detect_book('86―不存在的战区―Ep.4.epub', '86―不存在的战区―')
        self.assertEqual((d.volume, d.confidence), (4, 98))

    def test_auto_series_title_without_manual_title(self):
        d = detect_book('十二国记 1 月之影 影之海.epub')
        self.assertEqual((d.series_title, d.volume, d.volume_title),
                         ('十二国记', 1, '月之影 影之海'))
        d = detect_book('狼与香辛料 Vol.03 狼与琥珀色的忧郁.epub')
        self.assertEqual((d.series_title, d.volume, d.volume_title),
                         ('狼与香辛料', 3, '狼与琥珀色的忧郁'))

    def test_manual_volume_formats(self):
        for text in ('03', 'V03', 'Vol.03', 'Ep.03', '第3卷'):
            with self.subTest(text=text):
                self.assertEqual(parse_book_override(text), 3)


class LightNovelPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='novel_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.history = self.root / '.history'
        self.patch = patch.object(ops, '_storage', return_value=self.history)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def file(self, name, data=b'book'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def plan(self, **kwargs):
        return build_novel_plan(
            str(self.root), '十二国记', '{title} - {volume:02d} - {volume_title}', **kwargs)

    def test_book_extensions_scanned_anime_ignored(self):
        for i, ext in enumerate(('epub', 'mobi', 'azw3', 'pdf', 'txt', 'cbz'), 1):
            self.file(f'十二国记 {i}.{ext}')
        self.file('十二国记 E09.mkv')
        plan = self.plan()
        self.assertEqual(len(plan), 6)
        self.assertTrue(all(item.kind == '轻小说' for item in plan))

    def test_volume_title_template_and_sequence(self):
        self.file('十二国记 1 月之影 影之海.epub')
        self.file('十二国记 无编号 风之万里 黎明之空.epub')
        plan = self.plan(force_sequence=True, sequence_start=4)
        self.assertEqual([x.volume for x in plan], [4, 5])
        self.assertIn('月之影 影之海', Path(plan[0].new_path).name)

    def test_mixed_series_auto_grouping_when_title_blank(self):
        self.file('十二国记 1 月之影 影之海.epub')
        self.file('狼与香辛料 Vol.03 狼与琥珀色的忧郁.epub')
        plan = build_novel_plan(
            str(self.root), '', '{title} - {volume:02d} - {volume_title}')
        self.assertEqual(len(plan), 2)
        by_series = {item.series_title: item for item in plan}
        self.assertEqual(set(by_series), {'十二国记', '狼与香辛料'})
        self.assertEqual(len({item.group_id for item in plan}), 2)
        self.assertIn('十二国记 - 01 - 月之影 影之海.epub',
                      Path(by_series['十二国记'].new_path).name)
        self.assertIn('狼与香辛料 - 03 - 狼与琥珀色的忧郁.epub',
                      Path(by_series['狼与香辛料'].new_path).name)

    def test_force_sequence_restarts_for_each_auto_series(self):
        self.file('十二国记 第8卷.epub')
        self.file('狼与香辛料 Vol.12.epub')
        plan = build_novel_plan(
            str(self.root), '', '{title} - 第{volume:02d}卷',
            force_sequence=True, sequence_start=1)
        self.assertEqual({item.series_title: item.volume for item in plan},
                         {'十二国记': 1, '狼与香辛料': 1})

    def test_unnumbered_file_reuses_known_series_prefix(self):
        self.file('十二国记 第1卷 月之影 影之海.epub')
        self.file('十二国记 风之万里 黎明之空.epub')
        plan = build_novel_plan(
            str(self.root), '', '{title} - 第{volume:02d}卷',
            force_sequence=True, sequence_start=4)
        self.assertTrue(all(item.series_title == '十二国记' for item in plan))
        self.assertEqual([item.volume for item in plan], [4, 5])

    def test_missing_volume_requires_review(self):
        self.file('十二国记 风之万里 黎明之空.epub')
        self.assertTrue(self.plan()[0].status.startswith('待确认'))

    def test_rename_and_undo_epub(self):
        original = self.file('十二国记 第1卷.epub', b'epub bytes')
        plan = self.plan()
        self.assertEqual(plan[0].status, READY)
        target = Path(plan[0].new_path)
        self.assertTrue(ops.execute_plan(plan)['ok'])
        self.assertTrue(target.exists())
        self.assertTrue(ops.undo_last()['ok'])
        self.assertTrue(original.exists())


class LightNovelGuiTests(unittest.TestCase):
    def setUp(self):
        module = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'AnimeRenamer.pyw'), run_name='novel_ui_test')
        self.app = module['App']()
        self.app.withdraw()
        self.addCleanup(self.app.destroy)

    def test_mode_switch_changes_templates(self):
        self.app.content_type_var.set('轻小说')
        self.app.on_content_type_change()
        self.assertEqual(tuple(self.app._template_combo.cget('values')), tuple(NOVEL_TEMPLATES))
        self.assertIn('{volume:', self.app.template_var.get())
        self.assertIn('轻小说模式', self.app.status_var.get())


if __name__ == '__main__':
    unittest.main()
