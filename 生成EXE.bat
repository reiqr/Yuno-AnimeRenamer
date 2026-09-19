@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
  python -m PyInstaller --noconfirm --clean --onefile --windowed --name AnimeRenamer --add-data "assets;assets" --version-file windows_version_info.txt AnimeRenamer.pyw
) else (
  py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name AnimeRenamer --add-data "assets;assets" --version-file windows_version_info.txt AnimeRenamer.pyw
)
if %errorlevel%==0 (
  echo 构建完成：dist\AnimeRenamer.exe
) else (
  echo 构建失败。如未安装 PyInstaller，请运行 python -m pip install pyinstaller 后重试。
)
pause
