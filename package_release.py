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

    for exe_name in ['AnimeRenamer_FutureDiary.exe', 'AnimeRenamer.exe']:
        exe = output / exe_name
        if exe.exists():
            files.append((exe, exe_name))

    prefix = f'AnimeRenamer_v{VERSION}/'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for source, name in files:
            z.write(source, prefix + name)

    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert prefix + 'assets/app_icon.ico' in z.namelist()
        assert prefix + 'assets/app_icon.png' in z.namelist()
        assert prefix + 'assets/yuno_sidebar.png' in z.namelist()
        assert prefix + 'assets/yuno_sidebar_hd.png' in z.namelist()
        assert prefix + 'assets/yuno_banner.png' in z.namelist()

    print(archive)
    return archive


if __name__ == '__main__':
    package()
