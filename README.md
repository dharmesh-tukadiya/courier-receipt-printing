# Courier Slip Generator

A Python-based tool to generate courier slip PDFs from Visual FoxPro database files (DBF). Supports both web interface and command-line modes with professional 4-per-page courier slip layout.

## Features

- ✅ Connect to FoxPro DBF files (DLCHLN.DBF and PRTMST.DBF)
- ✅ Web interface with Bootstrap UI
- ✅ Command-line interface
- ✅ Date range filtering
- ✅ Party-specific or all-party slip generation
- ✅ Professional PDF layout with 4 courier slips per page (2x2 grid)
- ✅ Courier slip format matching industry standards
- ✅ Automatic file naming
- ✅ Error handling and logging
- ✅ Logo upload support

## Quick Start

### Option 1: Automatic Installation (Recommended)

1. Download all files to a folder
2. Double-click `install.bat` to install dependencies
3. Copy your `DLCHLN.DBF` and `PRTMST.DBF` files to the same folder
4. Double-click `run_web.bat` for web interface or `run_cli.bat` for CLI

### Option 2: Manual Installation

1. Install Python 3.8+ from https://python.org
2. Open command prompt in the project folder
3. Run: `pip install -r requirements.txt`
4. Copy your DBF files to the project folder

## Usage

### Web Interface (Recommended)

```batch
python app.py