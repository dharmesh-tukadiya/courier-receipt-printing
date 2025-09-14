@echo off
echo Installing Courier Receipt Generator...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Installing requirements...
pip install -r requirements.txt

if errorlevel 1 (
    echo Error installing requirements. Please check your internet connection.
    pause
    exit /b 1
)

echo.
echo Installation complete!
echo.
echo To run the application:
echo 1. Web Interface: Double-click run_web.bat or run 'python app.py'
echo 2. CLI Mode: Double-click run_cli.bat or run 'python app.py cli'
echo.
echo Make sure your DLCHLN.DBF and PRTMST.DBF files are in the same directory.
echo.
pause