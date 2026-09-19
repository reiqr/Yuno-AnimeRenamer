@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem Legacy Chinese compatibility entry. Keep all launch logic in run_app.bat.
if not exist "run_app.bat" (
  echo 未找到 run_app.bat，无法启动 AnimeRenamer。
  pause
  exit /b 1
)

call "run_app.bat"
exit /b %errorlevel%
