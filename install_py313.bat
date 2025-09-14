@echo off
echo Installing Courier Receipt Generator for Python 3.13...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8-3.12 from https://python.org
    pause
    exit /b 1
)

echo Python found. Upgrading pip first...
python -m pip install --upgrade pip

echo Installing packages one by one for better compatibility...

echo Installing Flask...
pip install Flask==3.0.0

echo Installing database packages...
pip install dbfread==2.0.7

echo Installing pandas (this may take a moment)...
pip install "pandas>=2.0.0"

echo Installing reportlab...
pip install "reportlab>=4.0.0"

echo Installing Pillow (trying latest compatible version)...
pip install "Pillow>=10.1.0"

echo Installing remaining packages...
pip install Jinja2 Werkzeug

REM Try pyodbc last as it might need compilation
echo Installing pyodbc...
pip install pyodbc || (
    echo pyodbc installation failed. Trying alternative...
    pip install pypyodbc
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