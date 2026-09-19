@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py -3"

set "DEFAULT_VERSION="
for /f "delims=" %%I in ('%PY% -c "from renamer_core import VERSION; print(VERSION)" 2^>nul') do set "DEFAULT_VERSION=%%I"
if not defined DEFAULT_VERSION goto :version_read_error

echo.
echo Current project version: %DEFAULT_VERSION%
set "PRODUCT_VERSION="
echo Enter another x.y.z only for a temporary build override; source VERSION will not change.
set /p "PRODUCT_VERSION=Release version [Enter = %DEFAULT_VERSION%]: "
if not defined PRODUCT_VERSION set "PRODUCT_VERSION=%DEFAULT_VERSION%"

set "BUILD_NO="
for /f %%I in ('git rev-list --count HEAD 2^>nul') do set "BUILD_NO=%%I"
if not defined BUILD_NO set "BUILD_NO=0"

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

%PY% tools\generate_version_info.py --output build\windows_version_info.txt --build %BUILD_NO% --product-version "%PRODUCT_VERSION%"
if errorlevel 1 goto :bad_version

set "EXE_BASE="
for /f "delims=" %%I in ('%PY% tools\generate_version_info.py --build %BUILD_NO% --product-version "%PRODUCT_VERSION%" --print-exe-basename') do set "EXE_BASE=%%I"
if not defined EXE_BASE (
  echo Failed to resolve versioned EXE name.
  goto :fail
)

echo.
echo Resolved build:
echo   ProductVersion = %PRODUCT_VERSION%
echo   BuildNumber    = %BUILD_NO%
echo   EXE            = %EXE_BASE%.exe
echo.

if not exist dist mkdir dist
rem Remove only the exact current build target. Preserve older builds and unrelated dist files.
rem Retry short-lived Explorer/antivirus locks; never kill processes automatically.
for /l %%R in (1,1,3) do (
  if exist "dist\%EXE_BASE%.exe" (
    del /f /q "dist\%EXE_BASE%.exe" >nul 2>nul
    if exist "dist\%EXE_BASE%.exe" timeout /t 1 /nobreak >nul
  )
)
if exist "dist\%EXE_BASE%.exe" goto :locked_exe

rem Bundle only assets referenced at runtime; build/test/history material stays outside the EXE.
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --noupx ^
  --name "%EXE_BASE%" ^
  --paths "%CD%\ui" ^
  --version-file "%CD%\build\windows_version_info.txt" ^
  --icon "%CD%\assets\app_icon.ico" ^
  --add-data "%CD%\assets\app_icon.png;assets" ^
  --add-data "%CD%\assets\empty_phone.png;assets" ^
  --add-data "%CD%\assets\yuno_sidebar.png;assets" ^
  --add-data "%CD%\assets\yuno_banner_dark.png;assets" ^
  --add-data "%CD%\assets\yuno_banner_dark_wide.png;assets" ^
  --add-data "%CD%\assets\yuno_banner_bright.png;assets" ^
  --add-data "%CD%\assets\yuno_banner_bright_wide.png;assets" ^
  --distpath "%CD%\dist" ^
  AnimeRenamer.pyw

if errorlevel 1 goto :fail

echo.
echo Build complete:
echo   dist\%EXE_BASE%.exe
echo   ProductVersion: %PRODUCT_VERSION%
echo   FileVersion: %PRODUCT_VERSION%.%BUILD_NO%
echo.
echo Existing unrelated files and older versioned builds in dist were preserved.
echo If Explorer still shows an old icon or version, run tools\refresh_icon_cache.bat once.
echo.
pause
exit /b 0

:locked_exe
echo.
echo Cannot replace dist\%EXE_BASE%.exe because Windows is still using it.
echo Close the running EXE first. If it is already closed, also close Explorer
echo Preview/Details panes for this EXE and wait for antivirus scanning to finish.
echo.
echo Running process check:
tasklist /fi "IMAGENAME eq %EXE_BASE%.exe" 2^>nul | findstr /i "%EXE_BASE%.exe"
echo.
echo Run build_exe.bat again after the lock is released.
goto :fail

:bad_version
echo.
echo Invalid release version.
echo Please use x.y.z, for example 0.3.1.
echo Press Enter at the version prompt to use the current source version automatically.
goto :fail


:version_read_error
echo.
echo Failed to read VERSION from renamer_core.py.
goto :fail

:fail
echo.
echo Build stopped without changing unrelated dist files.
echo.
pause
exit /b 1
