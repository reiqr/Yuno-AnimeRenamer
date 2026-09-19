@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem Legacy Chinese compatibility entry. Keep all build logic in build_exe.bat.
if not exist "build_exe.bat" (
  echo 未找到 build_exe.bat，无法构建 AnimeRenamer。
  pause
  exit /b 1
)

call "build_exe.bat"
exit /b %errorlevel%
