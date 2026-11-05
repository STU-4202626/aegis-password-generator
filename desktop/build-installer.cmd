@echo off
setlocal
cd /d "%~dp0"
echo.
echo  =====================================================
echo        AEGIS Windows Installer Builder
 echo  =====================================================
echo.
echo  This is for the developer building the installer.
echo  People installing AEGIS do not need Python.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0packaging\build_windows.ps1"
if errorlevel 1 (
    echo.
    echo BUILD FAILED. Check the message above for details.
    echo Verify the error above. Python 3.11+ 64-bit and Inno Setup 6.3+ are prerequisites.
) else (
    echo.
    echo SUCCESS. See installer-output for AEGIS-Setup-0.3.9-Windows-x64.exe.
)
echo.
pause
