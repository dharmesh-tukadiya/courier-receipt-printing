# Courier Receipt Generator

A Python-based tool to generate courier receipt PDFs from Visual FoxPro database files (DBF). Supports both web interface and command-line modes.

## Features

- ✅ Connect to FoxPro DBF files (DLCHLN.DBF and PRTMST.DBF)
- ✅ Web interface with Bootstrap UI
- ✅ Command-line interface
- ✅ Date range filtering
- ✅ Party-specific or all-party receipt generation
- ✅ Professional PDF layout with 4 receipts per page
- ✅ Barcode support for docket numbers
- ✅ Automatic file naming
- ✅ Error handling and logging

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
```

Then open http://localhost:5000 in your browser.

### Command Line Interface

```batch
python app.py cli
```

Follow the prompts to:
1. Enter date range
2. Select party (or choose all parties)
3. Generate PDF

## File Structure

```
courier-receipt-generator/
├── app.py                 # Main application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── templates/
│   └── index.html        # Web interface template
├── install.bat          # Windows installation script
├── run_web.bat          # Run web interface
├── run_cli.bat          # Run CLI mode
├── build_exe.bat        # Build standalone executable
├── courier_receipts.spec # PyInstaller configuration
├── DLCHLN.DBF           # Your dockets database file
├── PRTMST.DBF           # Your party master file
└── README.md            # This file
```

## Database Requirements

The tool expects two DBF files:

### DLCHLN.DBF (Dockets/Transactions)
Required fields:
- `DOCKET_NO` - Docket number
- `DATE` - Transaction date
- `PARTY_CODE` - Party identifier
- `ORIGIN` - Origin location (defaults to "BAVLA")
- `DESTINATION` - Destination location
- `REF_NO` - Reference number
- `WEIGHT` - Package weight
- `AMOUNT` - Transaction amount

### PRTMST.DBF (Party Master)
Required fields:
- `CODE` - Party code
- `NAME` - Party name
- `CITY` - City
- `PHONE` - Phone number
- `MOBILE` - Mobile number
- `ADR1`, `ADR2`, `ADR3` - Address lines

## PDF Output

- 4 receipts per page for easy printing
- Each receipt includes:
  - Header with docket number and barcode
  - Sender: "PHC - PRIMARY HEALTH CENTER - BAVLA"
  - Receiver: Party details from database
  - Date, origin, destination
  - Contact information
  - Placeholder fields for cash/card amounts

## File Naming

Generated PDFs are named: `Receipts_{PartyName}_{YYYYMMDD-YYYYMMDD}.pdf`

Examples:
- `Receipts_ABC_Company_20241201-20241231.pdf`
- `Receipts_All_Parties_20241201-20241231.pdf`

## Building Standalone Executable

To create a standalone EXE file:

```batch
build_exe.bat
```

The executable will be created in the `dist` folder and can run on any Windows machine without Python installed.

## Configuration

You can modify settings in `config.py`:

- Database file paths
- Default sender information
- Receipts per page
- Logging level

## Environment Variables

Set these environment variables to override defaults:

- `DLCHLN_PATH` - Path to dockets DBF file
- `PRTMST_PATH` - Path to party master DBF file
- `SECRET_KEY` - Flask secret key
- `DEBUG` - Enable debug mode (true/false)

## Troubleshooting

### Common Issues

1. **"Database connection failed"**
   - Ensure DBF files exist in the project folder
   - Check file permissions
   - Verify DBF files are not corrupted

2. **"No parties found"**
   - Check PRTMST.DBF has valid data
   - Ensure NAME field is not empty in records

3. **"No dockets found"**
   - Verify date range contains data
   - Check DATE field format in DLCHLN.DBF
   - Ensure PARTY_CODE matches between files

4. **PDF generation errors**
   - Check disk space
   - Verify write permissions in output folder
   - Review logs in `courier_receipts.log`

### Log Files

Check `courier_receipts.log` for detailed error information.

## Requirements

- Windows 10/11
- Python 3.8+ (for development)
- DBF files with required structure
- Internet connection (for initial setup)

## Support

For issues or questions:
1. Check the log file for error details
2. Verify your DBF files match the expected structure
3. Ensure all dependencies are installed correctly

## License

This tool is provided as-is for internal use. Modify as needed for your requirements.