@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py -3"

rem Always build from a clean directory so an old spec/resource cannot keep the old icon.
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist AnimeRenamer.spec del /q AnimeRenamer.spec
if exist AnimeRenamer_FutureDiary.spec del /q AnimeRenamer_FutureDiary.spec

%PY% -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo PyInstaller is not installed. Installing it now...
  %PY% -m pip install pyinstaller
  if errorlevel 1 goto :fail
)

%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --noupx ^
  --name AnimeRenamer_FutureDiary ^
  --version-file "%CD%\windows_version_info.txt" ^
  --icon "%CD%\assets\app_icon.ico" ^
  --add-data "%CD%\assets;assets" ^
  AnimeRenamer.pyw

if errorlevel 1 goto :fail

echo.
echo Build complete:
echo   dist\AnimeRenamer_FutureDiary.exe
echo.
echo A new executable name is used intentionally so Windows Explorer does not reuse
echo the cached icon from an older AnimeRenamer.exe.
echo If Explorer still shows an old icon, run refresh_icon_cache.bat once.
echo.
pause
exit /b 0

:fail
echo.
echo Build failed.
echo.
pause
exit /b 1
