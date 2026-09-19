import os
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools import generate_version_info as version_info
from tools import package_release as release
import renamer_core as core


UI_MODULES = [
    'ui_actions.py', 'ui_constants.py', 'ui_dialogs.py', 'ui_layout.py',
    'ui_light_novel.py', 'ui_styles.py', 'ui_theme.py', 'ui_view.py',
]


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


class VersionInfoTests(unittest.TestCase):
    def test_generated_file_version_uses_build_number(self):
        text = version_info.render_version_info(42, '1.2.3')
        self.assertIn("filevers=(1, 2, 3, 42)", text)
        self.assertIn("prodvers=(1, 2, 3, 0)", text)
        self.assertIn("StringStruct('FileVersion', '1.2.3.42')", text)
        self.assertIn("StringStruct('ProductVersion', '1.2.3')", text)

    def test_explicit_build_number_has_priority(self):
        with patch.dict(os.environ, {'GITHUB_RUN_NUMBER': '99'}, clear=False):
            self.assertEqual(version_info.resolve_build_number(7), 7)

    def test_github_run_number_is_supported(self):
        with patch.dict(os.environ, {'GITHUB_RUN_NUMBER': '88'}, clear=False):
            self.assertEqual(version_info.resolve_build_number(), 88)


class UiDisplayGuardTests(unittest.TestCase):
    def test_dpi_awareness_is_enabled_before_tk_import(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'AnimeRenamer.pyw').read_text(encoding='utf-8')
        call = source.index('_enable_windows_dpi_awareness()\n\n_ROOT')
        tk_import = source.index('import tkinter as tk')
        self.assertLess(call, tk_import)
        self.assertIn('SetProcessDpiAwarenessContext', source)

    def test_explicit_ui_font_sizes_stay_in_compact_readable_range(self):
        root = Path(__file__).resolve().parents[1]
        sizes = []
        pattern = re.compile(r"font=\(self\.FONTS\[[^\]]+\],\s*(\d+)")
        for path in (root / 'ui').glob('*.py'):
            sizes.extend(int(value) for value in pattern.findall(path.read_text(encoding='utf-8')))
        self.assertTrue(sizes)
        self.assertGreaterEqual(min(sizes), 7)
        self.assertLessEqual(max(sizes), 20)


class ReleasePackagingTests(unittest.TestCase):
    def _make_fixture(self, root):
        for name in [
            'AnimeRenamer.pyw', 'renamer_core.py', 'file_operations.py', *UI_MODULES,
            'README.md', 'CHANGELOG.md', 'LICENSE', 'build_exe.bat', 'package_release.py',
            'windows_version_info.txt', 'generate_version_info.py', 'refresh_icon_cache.bat', 'run_app.bat',
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
        return assets

    def test_license_is_included_and_legacy_exe_is_excluded(self):
        with tempfile.TemporaryDirectory(prefix='anime_release_') as td:
            root = Path(td)
            self._make_fixture(root)
            with patch.object(release, '__file__', str(root / 'package_release.py')):
                archive = release.package()
            with zipfile.ZipFile(archive) as z:
                names = set(z.namelist())
            prefix = f'AnimeRenamer_v{core.VERSION}/'
            self.assertIn(prefix + 'LICENSE', names)
            for module in UI_MODULES:
                self.assertIn(prefix + module, names)
            self.assertIn(prefix + 'AnimeRenamer_FutureDiary.exe', names)
            self.assertNotIn(prefix + 'AnimeRenamer.exe', names)
            self.assertFalse(any(Path(name).suffix.lower() in release.FONT_SUFFIXES for name in names))

    def test_font_asset_is_rejected_from_release(self):
        with tempfile.TemporaryDirectory(prefix='anime_release_font_') as td:
            root = Path(td)
            assets = self._make_fixture(root)
            (assets / 'should_not_ship.ttf').write_bytes(b'font')
            with patch.object(release, '__file__', str(root / 'package_release.py')):
                with self.assertRaisesRegex(RuntimeError, '字体文件'):
                    release.package()


if __name__ == '__main__':
    unittest.main()
