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
if exist "AnimeRenamer_FutureDiary_v*.spec" del /q "AnimeRenamer_FutureDiary_v*.spec"

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

set "BUILD_NO="
for /f %%I in ('git rev-list --count HEAD 2^>nul') do set "BUILD_NO=%%I"
if not defined BUILD_NO set "BUILD_NO=0"

%PY% tools\generate_version_info.py --output build\windows_version_info.txt --build %BUILD_NO%
if errorlevel 1 goto :fail

set "EXE_BASE="
for /f "delims=" %%I in ('%PY% -c "from tools.generate_version_info import exe_basename; print(exe_basename(%BUILD_NO%))"') do set "EXE_BASE=%%I"
if not defined EXE_BASE (
  echo Failed to resolve versioned EXE name.
  goto :fail
)

if not exist dist mkdir dist
rem Remove only the exact current build target. Preserve older builds and unrelated dist files.
if exist "dist\%EXE_BASE%.exe" del /q "dist\%EXE_BASE%.exe"

%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --noupx ^
  --name "%EXE_BASE%" ^
  --paths "%CD%\ui" ^
  --version-file "%CD%\build\windows_version_info.txt" ^
  --icon "%CD%\assets\app_icon.ico" ^
  --add-data "%CD%\assets;assets" ^
  --distpath "%CD%\dist" ^
  AnimeRenamer.pyw

if errorlevel 1 goto :fail

echo.
echo Build complete:
echo   dist\%EXE_BASE%.exe
echo   FileVersion and EXE filename use the current Git commit count as the build number.
echo.
echo Existing unrelated files and older versioned builds in dist were preserved.
echo If Explorer still shows an old icon or version, run tools\refresh_icon_cache.bat once.
echo.
pause
exit /b 0

:fail
echo.
echo Build stopped without changing unrelated dist files.
echo.
pause
exit /b 1
