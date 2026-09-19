@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

where pythonw >nul 2>nul
if not errorlevel 1 (
  start "" pythonw AnimeRenamer.pyw
  exit /b 0
)

where pyw >nul 2>nul
if not errorlevel 1 (
  start "" pyw -3 AnimeRenamer.pyw
  exit /b 0
)

where python >nul 2>nul
if not errorlevel 1 (
  python AnimeRenamer.pyw
  exit /b %errorlevel%
)

echo Python 3 was not found.
echo Install Python 3.10+ or build/use AnimeRenamer.exe.
pause
endlocal
