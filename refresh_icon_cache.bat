@echo off
rem Ask Windows Explorer to refresh shell icons without killing Explorer.
ie4uinit.exe -show >nul 2>nul
echo Icon refresh requested. Close and reopen the folder if necessary.
pause
