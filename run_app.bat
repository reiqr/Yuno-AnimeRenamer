@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "THEME_FONT_REG=assets\fonts\NotoSansCJKsc-Regular.otf"
set "THEME_FONT_BOLD=assets\fonts\NotoSansCJKsc-Bold.otf"
set "THEME_MONO_REG=assets\fonts\NotoSansMonoCJKsc-Regular.otf"
set "THEME_MONO_BOLD=assets\fonts\NotoSansMonoCJKsc-Bold.otf"
if not exist "%THEME_FONT_REG%" goto :prepare_fonts
if not exist "%THEME_FONT_BOLD%" goto :prepare_fonts
if not exist "%THEME_MONO_REG%" goto :prepare_fonts
if not exist "%THEME_MONO_BOLD%" goto :prepare_fonts
goto :fonts_ready

:prepare_fonts
echo Preparing bundled Noto CJK theme fonts for the visual preview...
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\download_theme_fonts.ps1"
if errorlevel 1 (
  echo.
  echo Theme font download failed. AnimeRenamer will continue with system fallback fonts.
  echo You can retry later with: powershell -ExecutionPolicy Bypass -File tools\download_theme_fonts.ps1
  echo.
)

:fonts_ready
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
