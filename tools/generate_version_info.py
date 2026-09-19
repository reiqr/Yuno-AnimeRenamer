"""Generate PyInstaller Windows version metadata from the app version and build number."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from renamer_core import VERSION

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_SOURCE_VERSION_RE = re.compile(r"(?m)^(VERSION\s*=\s*[\'\"])(\d+\.\d+\.\d+)([\'\"]\s*)$")
EXE_PREFIX = "AnimeRenamer_FutureDiary"


def parse_product_version(version: str = VERSION) -> tuple[int, int, int]:
    match = _VERSION_RE.fullmatch(version.strip())
    if not match:
        raise ValueError(f"VERSION 必须是 x.y.z 三段数字格式，当前为：{version!r}")
    parts = tuple(int(value) for value in match.groups())
    if any(value > 65535 for value in parts):
        raise ValueError("Windows 版本号每一段必须位于 0–65535")
    return parts



def remember_product_version(version: str, source_path: str | Path | None = None) -> str:
    """Persist only a newer x.y.z as the project default; never roll VERSION backward."""
    candidate = parse_product_version(version)
    source = Path(source_path) if source_path is not None else ROOT / "renamer_core.py"
    text = source.read_text(encoding="utf-8")
    match = _SOURCE_VERSION_RE.search(text)
    if not match:
        raise ValueError("无法在 renamer_core.py 中定位 VERSION")
    current = match.group(2)
    current_parts = parse_product_version(current)
    if candidate <= current_parts:
        return current
    updated = text[:match.start(2)] + version.strip() + text[match.end(2):]
    source.write_text(updated, encoding="utf-8")
    return version.strip()

def _git_commit_count() -> int | None:
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return int(result.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def resolve_build_number(explicit: int | None = None) -> int:
    if explicit is not None:
        build = explicit
    else:
        build = None
        for name in ("ANIMERENAMER_BUILD_NUMBER", "GITHUB_RUN_NUMBER"):
            value = os.environ.get(name, "").strip()
            if value:
                try:
                    build = int(value)
                except ValueError as exc:
                    raise ValueError(f"{name} 必须是整数") from exc
                break
        if build is None:
            build = _git_commit_count()
        if build is None:
            build = 0
    if not 0 <= build <= 65535:
        raise ValueError("构建号必须位于 0–65535")
    return build


def full_version(build: int, version: str = VERSION) -> str:
    parse_product_version(version)
    build_number = resolve_build_number(build)
    return f"{version}.{build_number}"


def exe_basename(build: int, version: str = VERSION) -> str:
    return f"{EXE_PREFIX}_v{full_version(build, version)}"


def exe_filename(build: int, version: str = VERSION) -> str:
    return exe_basename(build, version) + ".exe"


def render_version_info(build: int, version: str = VERSION) -> str:
    major, minor, patch = parse_product_version(version)
    build_number = resolve_build_number(build)
    file_version = full_version(build_number, version)
    original_filename = exe_filename(build_number, version)
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({major}, {minor}, {patch}, {build_number}), prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('080404b0', [
    StringStruct('FileDescription', 'AnimeRenamer - Future Diary Edition'),
    StringStruct('FileVersion', '{file_version}'),
    StringStruct('InternalName', '{EXE_PREFIX}'),
    StringStruct('OriginalFilename', '{original_filename}'),
    StringStruct('ProductName', 'AnimeRenamer'),
    StringStruct('ProductVersion', '{version}')
  ])]), VarFileInfo([VarStruct('Translation', [2052, 1200])])]
)
"""


def generate(output: str | Path, build: int | None = None, version: str = VERSION) -> Path:
    build_number = resolve_build_number(build)
    parse_product_version(version)
    target = Path(output)
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_version_info(build_number, version), encoding="utf-8")
    print(f"ProductVersion: {version}")
    print(f"FileVersion: {full_version(build_number, version)}")
    print(f"Executable: {exe_filename(build_number, version)}")
    print(target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Windows version info for PyInstaller")
    parser.add_argument("--output", default="build/windows_version_info.txt")
    parser.add_argument("--build", type=int, default=None)
    parser.add_argument("--product-version", default=VERSION)
    parser.add_argument("--print-exe-basename", action="store_true")
    parser.add_argument("--remember-product-version", action="store_true")
    args = parser.parse_args()
    try:
        version = args.product_version.strip()
        parse_product_version(version)
        if args.remember_product_version:
            remembered = remember_product_version(version)
            if remembered == version:
                print(f"Project version remembered: {remembered}")
            else:
                print(f"Project version remains: {remembered}; build override: {version}")
            return 0
        build_number = resolve_build_number(args.build)
        if args.print_exe_basename:
            print(exe_basename(build_number, version))
        else:
            generate(args.output, build_number, version)
    except (OSError, ValueError) as exc:
        print(f"version info generation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
