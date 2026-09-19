"""Create a clean release ZIP from the organized repository layout."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import zipfile


def _repo_root():
    script = Path(__file__).resolve()
    return script.parent.parent if script.parent.name == 'tools' else script.parent


ROOT = _repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from renamer_core import VERSION
from tools.generate_version_info import exe_filename, resolve_build_number

FONT_SUFFIXES = {'.ttf', '.otf', '.ttc', '.woff', '.woff2'}


def _git_commit_count(root):
    try:
        result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return int(result.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _release_build_number(root):
    value = os.environ.get('ANIMERENAMER_BUILD_NUMBER', '').strip()
    if value:
        try:
            return resolve_build_number(int(value))
        except ValueError as exc:
            raise RuntimeError('ANIMERENAMER_BUILD_NUMBER 必须是 0–65535 的整数') from exc
    git_count = _git_commit_count(root)
    return resolve_build_number(git_count if git_count is not None else 0)


def _release_exe_name(root):
    build_number = _release_build_number(root)
    expected = exe_filename(build_number, VERSION)
    configured = os.environ.get('ANIMERENAMER_EXE_NAME', '').strip()
    if not configured:
        return expected
    if Path(configured).name != configured:
        raise RuntimeError('ANIMERENAMER_EXE_NAME 只能是文件名，不能包含路径')
    if configured != expected:
        raise RuntimeError(
            f'ANIMERENAMER_EXE_NAME 与当前版本不一致：期望 {expected}，实际 {configured}')
    return configured


def package():
    root = _repo_root()
    output = root / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / f'AnimeRenamer_v{VERSION}.zip'

    files = []
    for name in [
        'AnimeRenamer.pyw', 'renamer_core.py', 'file_operations.py',
        'README.md', 'CHANGELOG.md', 'LICENSE', 'build_exe.bat', 'run_app.bat',
        '运行 AnimeRenamer.bat', '生成EXE.bat',
    ]:
        source = root / name
        if source.is_file():
            files.append((source, name))

    ui_dir = root / 'ui'
    if ui_dir.is_dir():
        files += [(p, p.relative_to(root).as_posix())
                  for p in sorted(ui_dir.glob('*.py')) if p.is_file()]
    else:
        # Transitional fallback for old test fixtures / pre-migration trees.
        files += [(p, p.name) for p in sorted(root.glob('ui_*.py'))]

    tools_dir = root / 'tools'
    if tools_dir.is_dir():
        files += [(p, p.relative_to(root).as_posix())
                  for p in sorted(tools_dir.iterdir())
                  if p.is_file() and p.name not in {'__pycache__', 'windows_version_info.txt'}]

    assets = root / 'assets'
    if assets.is_dir():
        font_assets = [p for p in assets.rglob('*')
                       if p.is_file() and p.suffix.lower() in FONT_SUFFIXES]
        if font_assets:
            names = ', '.join(p.relative_to(root).as_posix() for p in font_assets)
            raise RuntimeError(f'发布包禁止包含字体文件：{names}')
        files += [(p, p.relative_to(root).as_posix())
                  for p in sorted(assets.rglob('*')) if p.is_file()]

    tests = root / 'tests'
    if tests.is_dir():
        files += [(p, p.relative_to(root).as_posix())
                  for p in sorted(tests.glob('test_*.py'))]

    benchmarks = root / 'benchmarks'
    if benchmarks.is_dir():
        files += [(p, p.relative_to(root).as_posix())
                  for p in sorted(benchmarks.glob('*.py'))]

    expected_exe_name = _release_exe_name(root)
    exe = output / expected_exe_name
    if exe.exists():
        files.append((exe, exe.name))

    for stale in sorted(output.glob('AnimeRenamer*.exe')):
        if stale.name != expected_exe_name:
            print(f'warning: {stale.name} is stale and was NOT packaged.')

    prefix = f'AnimeRenamer_v{VERSION}/'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for source, name in files:
            z.write(source, prefix + name)

    with zipfile.ZipFile(archive) as z:
        names = set(z.namelist())
        assert z.testzip() is None
        assert prefix + 'LICENSE' in names
        assert prefix + 'assets/app_icon.ico' in names
        assert prefix + 'assets/app_icon.png' in names
        assert prefix + 'assets/yuno_sidebar.png' in names
        assert prefix + 'assets/yuno_sidebar_hd.png' in names
        assert prefix + 'assets/yuno_banner.png' in names
        if ui_dir.is_dir():
            for module in ui_dir.glob('*.py'):
                assert prefix + module.relative_to(root).as_posix() in names
        if exe.exists():
            assert prefix + exe.name in names
        assert prefix + 'AnimeRenamer.exe' not in names
        assert prefix + 'AnimeRenamer_FutureDiary.exe' not in names
        assert not any(Path(name).suffix.lower() in FONT_SUFFIXES for name in names)

    print(archive)
    return archive


if __name__ == '__main__':
    package()
