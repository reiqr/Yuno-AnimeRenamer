# UI Preview 15 — Windows icon and EXE build manifest

Preview 15 did not change the main UI source. It finalized Windows Explorer / taskbar icon handling and EXE packaging.

Source patch archive:
- `AnimeRenamer_FutureDiary_Icon_preview15_patch.zip`
- SHA256: `e68c56a44d37a5259e3fca818dd05697f053ae06a5704bf6dd3fd4234b8597a0`

Changed files:

| File | Size | SHA256 |
| --- | ---: | --- |
| `package_release.py` | 1,920 B | `c906c0d8d032a138ca8cf00281d81d7c2c220c9d696f2a229c102925726fbb5d` |
| `build_exe.bat` | 626 B | `85f5564657ead98a0ef8eca07e4c2ee0d25420221f0d2a1aca7332133dc7d1d2` |
| `assets/app_icon.png` | 70,906 B | `387425e007aaaef6187a28944611e9e6bb9c2786e03f6ab2016bb027ed62f832` |
| `assets/app_icon.ico` | 129,850 B | `a66ee064a449d96d1920dc6ac911a763a3a73c0977f22655dd9db993ce93f8b5` |

The generated `__pycache__/package_release.cpython-313.pyc` found in the local patch archive is intentionally **not** part of the source record.

Packaging intent:
- PyInstaller uses `--icon assets\app_icon.ico`;
- theme assets are bundled via `--add-data "assets;assets"`;
- the ICO contains multiple Windows-friendly sizes from small Explorer icons through 256×256.
