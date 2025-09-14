@echo off
echo Building executable...
echo.

REM Install PyInstaller if not present
pip install pyinstaller

REM Build the executable
pyinstaller courier_receipts.spec

if errorlevel 1 (
    echo Error building executable
    pause
    exit /b 1
)

echo.
echo Build complete! Executable is in the 'dist' folder.
echo.
pause