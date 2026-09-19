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
        self.assertIn(
            "StringStruct('OriginalFilename', 'AnimeRenamer_FutureDiary_v1.2.3.42.exe')",
            text,
        )

    def test_versioned_exe_name_uses_full_build_version(self):
        self.assertEqual(
            version_info.exe_filename(42, '1.2.3'),
            'AnimeRenamer_FutureDiary_v1.2.3.42.exe',
        )

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


    def test_preview_alignment_uses_single_boundary_and_full_width_columns(self):
        root = Path(__file__).resolve().parents[1]
        layout = (root / 'ui' / 'ui_layout.py').read_text(encoding='utf-8')
        view = (root / 'ui' / 'ui_view.py').read_text(encoding='utf-8')
        self.assertIn("preview.pack(fill='both', expand=True)", layout)
        self.assertIn("self.empty_state.place(relx=0.5, rely=0.50", layout)
        self.assertIn('self.tree.winfo_width() - 2', view)
        self.assertNotIn('self.tree.winfo_width() - 12', view)

    def test_larger_window_native_folder_drop_and_preview_filters_are_present(self):
        root = Path(__file__).resolve().parents[1]
        app = (root / 'AnimeRenamer.pyw').read_text(encoding='utf-8')
        actions = (root / 'ui' / 'ui_actions.py').read_text(encoding='utf-8')
        layout = (root / 'ui' / 'ui_layout.py').read_text(encoding='utf-8')
        self.assertIn('min(1392', app)
        self.assertIn('min(864', app)
        self.assertIn('DragAcceptFiles', actions)
        self.assertIn('SetWindowLongPtrW', actions)
        self.assertNotIn('tkinterdnd', actions.casefold())
        self.assertIn("self.preview_filter_var = tk.StringVar(value='全部')", layout)
        self.assertIn("text='只看问题'", layout)
        self.assertIn('command=self.select_visible_rows', layout)
        self.assertIn("text='跳过/恢复'", layout)

    def test_exe_builds_bundle_only_explicit_runtime_assets(self):
        root = Path(__file__).resolve().parents[1]
        batch = (root / 'build_exe.bat').read_text(encoding='utf-8')
        workflow = (root / '.github' / 'workflows' / 'python-app.yml').read_text(encoding='utf-8')
        runtime_assets = [
            'app_icon.png', 'empty_phone.png', 'yuno_sidebar.png',
            'yuno_banner_dark.png', 'yuno_banner_dark_wide.png',
            'yuno_banner_bright.png', 'yuno_banner_bright_wide.png',
        ]
        self.assertNotIn('assets;assets', batch)
        self.assertNotIn('$PWD\\assets;assets', workflow)
        for name in runtime_assets:
            self.assertIn(name, batch)
            self.assertIn(name, workflow)
        for dev_only in ['yuno_sidebar_hd.png', 'yuno_banner.png', 'yuno_banner_wide.png']:
            self.assertNotIn(f'--add-data "%CD%\\assets\\{dev_only};assets"', batch)
            self.assertNotIn(f'--add-data "$PWD\\assets\\{dev_only};assets"', workflow)



class ReleasePackagingTests(unittest.TestCase):
    BUILD_NO = 42

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
        current_exe = version_info.exe_filename(self.BUILD_NO, core.VERSION)
        (dist / current_exe).write_bytes(b'current')
        (dist / 'AnimeRenamer_FutureDiary.exe').write_bytes(b'old-unversioned')
        (dist / 'AnimeRenamer.exe').write_bytes(b'legacy')
        return assets, current_exe

    def test_license_is_included_and_legacy_exes_are_excluded(self):
        with tempfile.TemporaryDirectory(prefix='anime_release_') as td:
            root = Path(td)
            _, current_exe = self._make_fixture(root)
            env = {
                'ANIMERENAMER_BUILD_NUMBER': str(self.BUILD_NO),
                'ANIMERENAMER_EXE_NAME': current_exe,
            }
            with patch.object(release, '__file__', str(root / 'package_release.py')):
                with patch.dict(os.environ, env, clear=False):
                    archive = release.package()
            with zipfile.ZipFile(archive) as z:
                names = set(z.namelist())
            prefix = f'AnimeRenamer_v{core.VERSION}/'
            self.assertIn(prefix + 'LICENSE', names)
            for module in UI_MODULES:
                self.assertIn(prefix + module, names)
            self.assertIn(prefix + current_exe, names)
            self.assertNotIn(prefix + 'AnimeRenamer_FutureDiary.exe', names)
            self.assertNotIn(prefix + 'AnimeRenamer.exe', names)
            self.assertFalse(any(Path(name).suffix.lower() in release.FONT_SUFFIXES for name in names))

    def test_mismatched_configured_exe_name_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='anime_release_name_') as td:
            root = Path(td)
            self._make_fixture(root)
            env = {
                'ANIMERENAMER_BUILD_NUMBER': str(self.BUILD_NO),
                'ANIMERENAMER_EXE_NAME': 'AnimeRenamer_FutureDiary_v0.0.0.1.exe',
            }
            with patch.object(release, '__file__', str(root / 'package_release.py')):
                with patch.dict(os.environ, env, clear=False):
                    with self.assertRaisesRegex(RuntimeError, '当前版本不一致'):
                        release.package()

    def test_font_asset_is_rejected_from_release(self):
        with tempfile.TemporaryDirectory(prefix='anime_release_font_') as td:
            root = Path(td)
            assets, current_exe = self._make_fixture(root)
            (assets / 'should_not_ship.ttf').write_bytes(b'font')
            env = {
                'ANIMERENAMER_BUILD_NUMBER': str(self.BUILD_NO),
                'ANIMERENAMER_EXE_NAME': current_exe,
            }
            with patch.object(release, '__file__', str(root / 'package_release.py')):
                with patch.dict(os.environ, env, clear=False):
                    with self.assertRaisesRegex(RuntimeError, '字体文件'):
                        release.package()


if __name__ == '__main__':
    unittest.main()
