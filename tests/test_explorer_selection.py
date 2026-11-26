import unittest

from test_renamer import Workspace


class ExplorerSelectionTests(Workspace):
    def test_explicit_file_selection_does_not_import_neighbors(self):
        video = self.file('Show E01.mkv')
        subtitle = self.file('Show E01.chs.ass')
        self.file('Show E02.mkv')
        plan = self.plan(selected_paths=[video, subtitle])
        self.assertEqual({item.old_path for item in plan}, {str(video), str(subtitle)})

    def test_folders_keep_separate_groups_and_deduplicate(self):
        first = self.file('A/Show E03.mkv')
        second = self.file('B/Show E03.mkv')
        subdir = self.file('A/Extras/Show SP01.mkv')
        self.file('Other/Show E01.mkv')
        selected = [first.parent, second.parent, first]
        plan = self.plan(selected_paths=selected)
        self.assertEqual({item.group for item in plan}, {'A', 'B'})
        self.assertEqual(len(plan), 2)
        recursive = self.plan(selected_paths=selected, recursive=True)
        self.assertEqual({x.old_path for x in recursive}, {str(first), str(second), str(subdir)})

    def test_deleted_selection_does_not_fall_back_to_directory(self):
        self.file('Show E01.mkv')
        with self.assertRaisesRegex(ValueError, '已不存在'):
            self.plan(selected_paths=[self.source / 'deleted.mkv'])
