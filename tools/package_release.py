"""Create a clean release ZIP from the organized repository layout."""
from __future__ import annotations

from pathlib import Path
import sys
import zipfile


def _repo_root():
    script = Path(__file__).resolve()
    return script.parent.parent if script.parent.name == 'tools' else script.parent


ROOT = _repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from renamer_core import VERSION


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
                  if p.is_file() and p.name != '__pycache__']

    assets = root / 'assets'
    if assets.is_dir():
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

    exe = output / 'AnimeRenamer_FutureDiary.exe'
    if exe.exists():
        files.append((exe, exe.name))
    stale = output / 'AnimeRenamer.exe'
    if stale.exists():
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
        assert prefix + 'AnimeRenamer.exe' not in names

    print(archive)
    return archive


if __name__ == '__main__':
    package()
