@echo off
chcp 65001 >nul
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw AnimeRenamer.pyw
  exit /b
)
where pyw >nul 2>nul
if %errorlevel%==0 (
  start "" pyw -3 AnimeRenamer.pyw
  exit /b
)
echo 未检测到 Python，请安装 Python 3.10 或更高版本，或使用打包后的 AnimeRenamer.exe。
pause
