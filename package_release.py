"""Create a UTF-8-named release ZIP without caches, local data or git internals."""
from pathlib import Path
import zipfile

from renamer_core import VERSION


def package():
    root = Path(__file__).resolve().parent
    output = root / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / f'AnimeRenamer_v{VERSION}.zip'
    names = ['AnimeRenamer.pyw', 'renamer_core.py', 'file_operations.py', 'README.md',
             'CHANGELOG.md', '运行 AnimeRenamer.bat', '生成EXE.bat',
             'package_release.py', 'windows_version_info.txt']
    files = [(root / name, name) for name in names]
    files += [(p, p.relative_to(root).as_posix()) for p in sorted((root / 'tests').glob('test_*.py'))]
    exe = output / 'AnimeRenamer.exe'
    if exe.exists():
        files.append((exe, 'AnimeRenamer.exe'))
    prefix = f'AnimeRenamer_v{VERSION}/'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for source, name in files:
            z.write(source, prefix + name)
    # Zipfile automatically sets bit 11 when non-ASCII names are encoded as UTF-8.
    with zipfile.ZipFile(archive) as z:
        for name in ['运行 AnimeRenamer.bat', '生成EXE.bat']:
            assert z.getinfo(prefix + name).flag_bits & 0x800
        assert z.testzip() is None
    print(archive)
    return archive


if __name__ == '__main__':
    package()
