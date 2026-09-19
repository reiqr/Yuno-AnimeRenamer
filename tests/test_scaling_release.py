import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import package_release as release
import renamer_core as core


class IndexedSubtitleMatchingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='anime_index_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def file(self, name):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding='utf-8')
        return path

    def plan(self, **kwargs):
        return core.build_plan(str(self.root), '作品', 1, '{title} - {episode:02d}', **kwargs)

    def test_longest_stem_prefix_is_preserved(self):
        self.file('Show.mkv')
        specific = self.file('Show E03.mkv')
        self.file('Show E03.chs.ass')
        plan = self.plan(overrides={str(specific): '12'})
        subtitle = next(item for item in plan if item.kind == '字幕')
        self.assertEqual(subtitle.episode, 12)
        self.assertEqual(subtitle.reason, '跟随同目录视频')

    def test_duplicate_video_stem_remains_ambiguous(self):
        self.file('Show E03.mkv')
        self.file('Show E03.mp4')
        self.file('Show E03.ass')
        subtitle = next(item for item in self.plan() if item.kind == '字幕')
        self.assertTrue(subtitle.status.startswith('待确认'))


class ReleasePackagingTests(unittest.TestCase):
    def test_license_is_included_and_legacy_exe_is_excluded(self):
        with tempfile.TemporaryDirectory(prefix='anime_release_') as td:
            root = Path(td)
            for name in [
                'AnimeRenamer.pyw', 'renamer_core.py', 'file_operations.py', 'README.md',
                'CHANGELOG.md', 'LICENSE', 'build_exe.bat', 'package_release.py',
                'windows_version_info.txt', 'refresh_icon_cache.bat', 'run_app.bat',
                '运行 AnimeRenamer.bat', '生成EXE.bat',
            ]:
                (root / name).write_text(name, encoding='utf-8')
            assets = root / 'assets'
            assets.mkdir()
            for name in ['app_icon.ico', 'app_icon.png', 'yuno_sidebar.png',
                         'yuno_sidebar_hd.png', 'yuno_banner.png']:
                (assets / name).write_bytes(b'asset')
            dist = root / 'dist'
            dist.mkdir()
            (dist / 'AnimeRenamer_FutureDiary.exe').write_bytes(b'current')
            (dist / 'AnimeRenamer.exe').write_bytes(b'legacy')

            with patch.object(release, '__file__', str(root / 'package_release.py')):
                archive = release.package()
            with zipfile.ZipFile(archive) as z:
                names = set(z.namelist())
            prefix = f'AnimeRenamer_v{core.VERSION}/'
            self.assertIn(prefix + 'LICENSE', names)
            self.assertIn(prefix + 'AnimeRenamer_FutureDiary.exe', names)
            self.assertNotIn(prefix + 'AnimeRenamer.exe', names)


if __name__ == '__main__':
    unittest.main()
