"""Create a clean release ZIP including the themed assets and optional EXE."""
from pathlib import Path
import zipfile

from renamer_core import VERSION


def package():
    root = Path(__file__).resolve().parent
    output = root / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / f'AnimeRenamer_v{VERSION}.zip'

    names = [
        'AnimeRenamer.pyw',
        'renamer_core.py',
        'file_operations.py',
        'README.md',
        'CHANGELOG.md',
        'LICENSE',
        'build_exe.bat',
        'package_release.py',
        'windows_version_info.txt',
        'refresh_icon_cache.bat',
    ]
    files = []
    for name in names:
        source = root / name
        if source.is_file():
            files.append((source, name))

    # UI was split into small ui_*.py modules. Discover them automatically so future
    # UI refactors do not require maintaining a second hard-coded release list.
    ui_modules = sorted(root.glob('ui_*.py'))
    files += [(module, module.name) for module in ui_modules]

    # Keep legacy launch/build helpers when they are present, but do not require them.
    for name in ['运行 AnimeRenamer.bat', '生成EXE.bat', 'run_app.bat']:
        source = root / name
        if source.is_file():
            files.append((source, name))

    assets = root / 'assets'
    if assets.is_dir():
        files += [
            (p, p.relative_to(root).as_posix())
            for p in sorted(assets.rglob('*')) if p.is_file()
        ]

    tests = root / 'tests'
    if tests.is_dir():
        files += [
            (p, p.relative_to(root).as_posix())
            for p in sorted(tests.glob('test_*.py'))
        ]

    # Ship only the current build target. A stale AnimeRenamer.exe must never ride along.
    exe = output / 'AnimeRenamer_FutureDiary.exe'
    if exe.exists():
        files.append((exe, exe.name))
    stale = output / 'AnimeRenamer.exe'
    if stale.exists():
        print(f'warning: {stale.name} is a stale build and was NOT packaged. Delete it to avoid confusion.')

    prefix = f'AnimeRenamer_v{VERSION}/'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for source, name in files:
            z.write(source, prefix + name)

    with zipfile.ZipFile(archive) as z:
        names_in_zip = set(z.namelist())
        assert z.testzip() is None
        assert prefix + 'assets/app_icon.ico' in names_in_zip
        assert prefix + 'assets/app_icon.png' in names_in_zip
        assert prefix + 'assets/yuno_sidebar.png' in names_in_zip
        assert prefix + 'assets/yuno_sidebar_hd.png' in names_in_zip
        assert prefix + 'assets/yuno_banner.png' in names_in_zip
        assert prefix + 'LICENSE' in names_in_zip
        for module in ui_modules:
            assert prefix + module.name in names_in_zip
        assert prefix + 'AnimeRenamer.exe' not in names_in_zip

    print(archive)
    return archive


if __name__ == '__main__':
    package()
