@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py -3"

rem Only clear generated build cache/spec files. Never delete the whole dist directory.
if exist build rmdir /s /q build
if exist AnimeRenamer.spec del /q AnimeRenamer.spec
if exist AnimeRenamer_FutureDiary.spec del /q AnimeRenamer_FutureDiary.spec

%PY% -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo.
  echo PyInstaller is required but is not installed.
  echo This script will NOT install or upgrade packages automatically.
  echo.
  echo Dependency : PyInstaller
  echo Source     : Python Package Index ^(PyPI^) / https://pypi.org/project/pyinstaller/
  echo Purpose    : Package AnimeRenamer.pyw as a Windows executable.
  echo Risk       : Installing a Python package changes the selected Python environment and may pull transitive dependencies.
  echo.
  echo If you have reviewed and approved the dependency, install it manually with:
  echo   %PY% -m pip install pyinstaller
  echo Then run build_exe.bat again.
  echo.
  goto :fail
)

if not exist dist mkdir dist
rem Remove only this build target so unrelated release ZIPs/files in dist are preserved.
if exist "dist\AnimeRenamer_FutureDiary.exe" del /q "dist\AnimeRenamer_FutureDiary.exe"

%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --noupx ^
  --name AnimeRenamer_FutureDiary ^
  --paths "%CD%\ui" ^
  --version-file "%CD%\tools\windows_version_info.txt" ^
  --icon "%CD%\assets\app_icon.ico" ^
  --add-data "%CD%\assets;assets" ^
  --distpath "%CD%\dist" ^
  AnimeRenamer.pyw

if errorlevel 1 goto :fail

echo.
echo Build complete:
echo   dist\AnimeRenamer_FutureDiary.exe
echo.
echo Existing unrelated files in dist were preserved.
echo If Explorer still shows an old icon, run tools\refresh_icon_cache.bat once.
echo.
pause
exit /b 0

:fail
echo.
echo Build stopped without changing unrelated dist files.
echo.
pause
exit /b 1
