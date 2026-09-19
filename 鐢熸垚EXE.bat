@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if not %errorlevel%==0 (
  echo 未检测到 Python Launcher (py)。
  echo 请先安装 Python 3.10 或更高版本。
  pause
  exit /b 1
)
py -m pip install --upgrade pyinstaller
if not %errorlevel%==0 (
  echo PyInstaller 安装失败。
  pause
  exit /b 1
)
py -m PyInstaller --noconfirm --clean --onefile --windowed --name AnimeRenamer AnimeRenamer.pyw
if %errorlevel%==0 (
  echo.
  echo 构建完成：dist\AnimeRenamer.exe
) else (
  echo.
  echo 构建失败，请查看上面的错误信息。
)
pause
