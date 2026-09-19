@echo off
chcp 65001 >nul
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw AnimeRenamer.pyw
  exit /b
)
where py >nul 2>nul
if %errorlevel%==0 (
  start "" pyw AnimeRenamer.pyw
  exit /b
)
echo 未检测到 Python。
echo 请先安装 Python 3.10 或更高版本，并勾选 Add Python to PATH。
pause
