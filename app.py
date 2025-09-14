import os
import sys
import logging
from datetime import datetime, date
from flask import Flask, render_template, request, send_file, jsonify, flash, redirect, url_for
import tempfile
from werkzeug.utils import secure_filename

# Try importing database libraries
try:
    import pyodbc
    HAS_PYODBC = True
except ImportError:
    try:
        import pypyodbc as pyodbc
        HAS_PYODBC = True
    except ImportError:
        HAS_PYODBC = False

try:
    from dbfread import DBF
    HAS_DBFREAD = True
except ImportError:
    HAS_DBFREAD = False

# Try importing other required libraries
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm, cm
    from reportlab.lib import colors
    from reportlab.graphics.barcode import code128
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('courier_receipts.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

def check_dependencies():
    """Check if all required dependencies are available"""
    missing = []
    
    if not HAS_DBFREAD:
        missing.append("dbfread")
    if not HAS_REPORTLAB:
        missing.append("reportlab")
    if not HAS_PYODBC:
        missing.append("pyodbc or pypyodbc")
    if not HAS_PIL:
        missing.append("Pillow")
    
    return missing

class DatabaseManager:
    def __init__(self, dlchln_path=None, prtmst_path=None):
        self.dlchln_path = dlchln_path or 'DLCHLN.DBF'
        self.prtmst_path = prtmst_path or 'PRTMST.DBF'
        
        # Common DBF encodings to try
        self.encodings = [
            'cp1252',  # Windows Western European
            'cp850',   # DOS Latin-1
            'cp437',   # DOS US
            'latin1',  # ISO 8859-1
            'utf-8',   # UTF-8
            'ascii',   # ASCII (last resort)
        ]
        
    def read_dbf_with_encoding(self, file_path):
        """Try to read DBF file with different encodings"""
        for encoding in self.encodings:
            try:
                logger.info(f"Trying to read {file_path} with encoding: {encoding}")
                dbf = DBF(file_path, encoding=encoding)
                # Test reading by getting first record
                test_records = list(dbf)
                logger.info(f"Successfully read {file_path} with encoding: {encoding}, records: {len(test_records)}")
                return dbf, encoding
            except Exception as e:
                logger.debug(f"Failed to read with {encoding}: {str(e)}")
                continue
        
        raise Exception(f"Could not read {file_path} with any supported encoding")
    
    def test_connection(self):
        """Test if DBF files exist and are readable"""
        if not HAS_DBFREAD:
            logger.error("dbfread library not available")
            return False
            
        try:
            if not os.path.exists(self.dlchln_path):
                raise FileNotFoundError(f"DLCHLN.DBF not found at {self.dlchln_path}")
            if not os.path.exists(self.prtmst_path):
                raise FileNotFoundError(f"PRTMST.DBF not found at {self.prtmst_path}")
            
            # Test reading with proper encoding
            dlchln, dlchln_encoding = self.read_dbf_with_encoding(self.dlchln_path)
            prtmst, prtmst_encoding = self.read_dbf_with_encoding(self.prtmst_path)
            
            dlchln_count = len(list(dlchln))
            prtmst_count = len(list(prtmst))
            
            logger.info(f"Successfully connected to DBF files")
            logger.info(f"DLCHLN records: {dlchln_count} (encoding: {dlchln_encoding})")
            logger.info(f"PRTMST records: {prtmst_count} (encoding: {prtmst_encoding})")
            
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return False
    
    def get_parties(self):
        """Get all parties from PRTMST.DBF"""
        if not HAS_DBFREAD:
            logger.error("dbfread library not available")
            return []
            
        try:
            logger.info("Starting to load parties...")
            prtmst, encoding = self.read_dbf_with_encoding(self.prtmst_path)
            parties = []
            
            # Read DBF again for actual processing
            prtmst = DBF(self.prtmst_path, encoding=encoding)
            
            for i, record in enumerate(prtmst):
                try:
                    # Use correct field names from your database
                    name = record.get('PRTNM')  # Party Name
                    code = record.get('PRTCD')  # Party Code
                    
                    # Skip records without name or code
                    if not name or not code:
                        continue
                        
                    # Clean up the data
                    party = {
                        'code': str(code).strip(),
                        'name': str(name).strip(),
                        'city': str(record.get('CITY', '')).strip(),
                        'phone': str(record.get('PHONE_1', '')).strip(),
                        'mobile': str(record.get('MOBILE', '')).strip(),
                        'adr1': str(record.get('ADR1', '')).strip(),
                        'adr2': str(record.get('ADR2', '')).strip(),
                        'adr3': str(record.get('ADR3', '')).strip()
                    }
                    
                    # Only add if name is not empty after stripping
                    if party['name'] and party['code']:
                        parties.append(party)
                        
                except Exception as e:
                    logger.warning(f"Error processing party record {i}: {str(e)}")
                    continue
            
            # Sort by name
            parties.sort(key=lambda x: x['name'])
            logger.info(f"Successfully retrieved {len(parties)} parties")
            
            return parties
            
        except Exception as e:
            logger.error(f"Error retrieving parties: {str(e)}")
            return []
    
    def get_dockets(self, start_date, end_date, party_code=None):
        """Get dockets from DLCHLN.DBF within date range and optionally for specific party"""
        if not HAS_DBFREAD:
            return []
            
        try:
            logger.info(f"Loading dockets from {start_date} to {end_date}, party: {party_code}")
            dlchln, encoding = self.read_dbf_with_encoding(self.dlchln_path)
            dockets = []
            
            # Read DBF again for actual processing
            dlchln = DBF(self.dlchln_path, encoding=encoding)
            
            for i, record in enumerate(dlchln):
                try:
                    record_date = record.get('DATE')
                    if record_date:
                        # Convert date if needed
                        if isinstance(record_date, str):
                            try:
                                record_date = datetime.strptime(record_date, '%Y-%m-%d').date()
                            except:
                                try:
                                    record_date = datetime.strptime(record_date, '%d/%m/%Y').date()
                                except:
                                    try:
                                        record_date = datetime.strptime(record_date, '%m/%d/%Y').date()
                                    except:
                                        continue
                        elif isinstance(record_date, datetime):
                            record_date = record_date.date()
                        
                        if start_date <= record_date <= end_date:
                            # Use PRTCD field from DLCHLN
                            record_party_code = str(record.get('PRTCD', '')).strip()
                            if party_code is None or record_party_code == str(party_code).strip():
                                dockets.append({
                                    'docket_no': str(record.get('DOC_NO', '')).strip(),
                                    'date': record_date,
                                    'party_code': record_party_code,
                                    'origin': 'BAVLA',
                                    'destination': str(record.get('CITY', '')).strip(),
                                    'ref_no': str(record.get('REMARK', '')).strip(),
                                    'weight': float(record.get('WEIGHT', 0)) if record.get('WEIGHT') else 0,
                                    'amount': float(record.get('AMOUNT', 0)) if record.get('AMOUNT') else 0,
                                    'party_name': str(record.get('PARTY', '')).strip()
                                })
                except Exception as e:
                    logger.warning(f"Error processing docket record {i}: {str(e)}")
                    continue
            
            logger.info(f"Retrieved {len(dockets)} dockets")
            return dockets
        except Exception as e:
            logger.error(f"Error retrieving dockets: {str(e)}")
            return []

# Initialize components
db_manager = DatabaseManager()

@app.route('/')
def index():
    """Main page"""
    missing_deps = check_dependencies()
    return render_template('index.html', missing_dependencies=missing_deps)

@app.route('/api/dependencies')
def check_deps():
    """Check dependencies API"""
    missing = check_dependencies()
    return jsonify({'missing': missing, 'all_available': len(missing) == 0})

@app.route('/api/parties')
def get_parties():
    """API endpoint to get all parties"""
    try:
        logger.info("API: Getting parties...")
        parties = db_manager.get_parties()
        logger.info(f"API: Returning {len(parties)} parties")
        return jsonify(parties)
    except Exception as e:
        logger.error(f"API Error getting parties: {str(e)}")
        return jsonify([])

@app.route('/api/test-connection')
def test_connection():
    """Test database connection"""
    try:
        logger.info("API: Testing connection...")
        success = db_manager.test_connection()
        logger.info(f"API: Connection test result: {success}")
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"API Error testing connection: {str(e)}")
        return jsonify({'success': False})

@app.route('/api/dockets')
def get_dockets_api():
    """API endpoint to get dockets data"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        party_code = request.args.get('party_code')
        
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'Missing date parameters'}), 400
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Get dockets
        dockets = db_manager.get_dockets(start_date, end_date, party_code)
        
        # Get parties for mapping
        parties = db_manager.get_parties()
        parties_map = {p['code']: p for p in parties}
        
        # Enhance dockets with party information
        enhanced_dockets = []
        for docket in dockets:
            party_info = parties_map.get(docket.get('party_code'), {})
            
            # Format consignee info
            consignee_parts = []
            if party_info.get('name'):
                consignee_parts.append(party_info['name'])
            if party_info.get('adr1'):
                consignee_parts.append(party_info['adr1'])
            if party_info.get('adr2'):
                consignee_parts.append(party_info['adr2'])
            if party_info.get('city'):
                consignee_parts.append(party_info['city'])
            if party_info.get('phone'):
                consignee_parts.append(f"Phone: {party_info['phone']}")
            
            enhanced_docket = {
                'docket_no': docket['docket_no'],
                'date': docket['date'].strftime('%d/%m/%Y'),
                'origin': docket['origin'],
                'destination': docket['destination'],
                'consignor': 'PHC - PRIMARY HEALTH CENTER - BAVLA',
                'consignee': '\n'.join(consignee_parts) if consignee_parts else docket.get('party_name', ''),
                'ref_no': docket['ref_no'],
                'weight': docket['weight'],
                'amount': docket['amount']
            }
            enhanced_dockets.append(enhanced_docket)
        
        return jsonify({'success': True, 'dockets': enhanced_dockets})
        
    except Exception as e:
        logger.error(f"Error getting dockets: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/courier-slips')
def courier_slips():
    """Render courier slips page with data"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        party_code = request.args.get('party_code')
        
        if not start_date_str or not end_date_str:
            return "Missing date parameters", 400
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Get dockets
        dockets = db_manager.get_dockets(start_date, end_date, party_code)
        
        if not dockets:
            return render_template('courier_slips.html', dockets=[], message="No dockets found for the selected criteria")
        
        # Get parties for mapping
        parties = db_manager.get_parties()
        parties_map = {p['code']: p for p in parties}
        
        # Enhance dockets with party information
        enhanced_dockets = []
        for docket in dockets:
            party_info = parties_map.get(docket.get('party_code'), {})
            
            # Format consignee info
            consignee_parts = []
            if party_info.get('name'):
                consignee_parts.append(party_info['name'])
            if party_info.get('adr1'):
                consignee_parts.append(party_info['adr1'])
            if party_info.get('adr2'):
                consignee_parts.append(party_info['adr2'])
            if party_info.get('city'):
                consignee_parts.append(party_info['city'])
            if party_info.get('phone'):
                consignee_parts.append(f"Phone: {party_info['phone']}")
            
            enhanced_docket = {
                'docket_no': docket['docket_no'],
                'date': docket['date'].strftime('%d/%m/%Y'),
                'origin': docket['origin'],
                'destination': docket['destination'],
                'consignor': 'PHC - PRIMARY HEALTH CENTER - BAVLA',
                'consignee': '<br>'.join(consignee_parts) if consignee_parts else docket.get('party_name', ''),
                'ref_no': docket['ref_no'],
                'weight': docket['weight'],
                'amount': docket['amount']
            }
            enhanced_dockets.append(enhanced_docket)
        
        return render_template('courier_slips.html', dockets=enhanced_dockets)
        
    except Exception as e:
        logger.error(f"Error in courier_slips: {str(e)}")
        return f"Error: {str(e)}", 500

def cli_mode():
    """Command line interface mode"""
    print("\n=== Courier Slip Generator - CLI Mode ===\n")
    
    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print(f"Error: Missing dependencies: {', '.join(missing_deps)}")
        print("Please run install_py313.bat to install missing packages.")
        return
    
    # Test connection
    print("Testing database connection...")
    if not db_manager.test_connection():
        print("Error: Cannot connect to database files. Please check file paths.")
        return
    
    # Get parties
    print("Loading parties...")
    parties = db_manager.get_parties()
    if not parties:
        print("Error: No parties found in database.")
        return
    
    # Date input
    while True:
        try:
            start_date_str = input("Enter start date (YYYY-MM-DD): ")
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            
            end_date_str = input("Enter end date (YYYY-MM-DD): ")
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if start_date <= end_date:
                break
            else:
                print("Start date must be before or equal to end date.")
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
    
    # Party selection
    print(f"\nAvailable parties ({len(parties)}):")
    for i, party in enumerate(parties[:10]):  # Show first 10
        print(f"{i+1}. {party['name']} ({party['code']})")
    
    if len(parties) > 10:
        print(f"... and {len(parties) - 10} more parties")
    
    print("0. All parties")
    
    while True:
        try:
            choice = input("\nSelect party (enter number or party code): ")
            if choice == "0":
                party_code = None
                party_name = "All_Parties"
                break
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(parties):
                    party_code = parties[idx]['code']
                    party_name = parties[idx]['name']
                    break
            else:
                # Try to find by code
                for party in parties:
                    if party['code'].upper() == choice.upper():
                        party_code = party['code']
                        party_name = party['name']
                        break
                else:
                    print("Invalid selection.")
                    continue
                break
        except ValueError:
            print("Invalid input.")
    
    # Open in browser
    party_param = f"&party_code={party_code}" if party_code else ""
    url = f"http://localhost:5000/courier-slips?start_date={start_date}&end_date={end_date}{party_param}"
    
    print(f"\nOpening courier slips in browser...")
    print(f"URL: {url}")
    print("The slips will open in your default browser. You can print them directly from there.")
    
    import webbrowser
    webbrowser.open(url)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'cli':
        cli_mode()
    else:
        print("Starting web interface...")
        print("Open http://localhost:5000 in your browser")
        app.run(debug=True, host='0.0.0.0', port=5000)