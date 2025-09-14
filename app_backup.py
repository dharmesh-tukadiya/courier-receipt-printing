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
    import weasyprint
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False

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

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_dependencies():
    """Check if all required dependencies are available"""
    missing = []
    
    if not HAS_DBFREAD:
        missing.append("dbfread")
    if not HAS_WEASYPRINT:
        missing.append("weasyprint")
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

class PDFGenerator:
    def __init__(self, logo_path=None):
        if not HAS_WEASYPRINT:
            raise ImportError("weasyprint library not available")
            
        self.logo_path = logo_path
        
    def generate_pdf(self, dockets, parties_map, output_path):
        """Generate PDF using HTML template and WeasyPrint"""
        try:
            # Organize dockets into pages (4 per page)
            docket_pages = []
            for i in range(0, len(dockets), 4):
                page_dockets = dockets[i:i+4]
                
                # Add party info to each docket
                for docket in page_dockets:
                    party_info = parties_map.get(docket['party_code'], {
                        'name': docket.get('party_name', 'Unknown Party'),
                        'city': docket.get('destination', ''),
                        'phone': '',
                        'mobile': '',
                        'adr1': '',
                        'adr2': '',
                        'adr3': ''
                    })
                    docket['party_info'] = party_info
                    
                    # Add default consignor info (you can modify this as needed)
                    docket['consignor_name'] = 'Shree Balaji Courier Services'
                    docket['consignor_address'] = '15, Madhav Complex, Nr. Bavla Sanand Chokdi'
                    docket['consignor_city'] = 'Bavla - 382220'
                    docket['consignor_phone'] = ''
                
                docket_pages.append(page_dockets)
            
            # Render HTML template
            html_content = render_template('pdf_template.html', docket_pages=docket_pages)
            
            # Generate PDF from HTML
            weasyprint.HTML(string=html_content).write_pdf(output_path)
            
class PDFGenerator:
    def __init__(self, logo_path=None):
        if not HAS_WEASYPRINT:
            raise ImportError("weasyprint library not available")
            
        self.logo_path = logo_path
        
    def generate_pdf(self, dockets, parties_map, output_path):
        """Generate PDF using HTML template and WeasyPrint"""
        try:
            # Organize dockets into pages (4 per page)
            docket_pages = []
            for i in range(0, len(dockets), 4):
                page_dockets = dockets[i:i+4]
                
                # Add party info to each docket
                for docket in page_dockets:
                    party_info = parties_map.get(docket['party_code'], {
                        'name': docket.get('party_name', 'Unknown Party'),
                        'city': docket.get('destination', ''),
                        'phone': '',
                        'mobile': '',
                        'adr1': '',
                        'adr2': '',
                        'adr3': ''
                    })
                    docket['party_info'] = party_info
                    
                    # Add default consignor info (you can modify this as needed)
                    docket['consignor_name'] = 'Shree Balaji Courier Services'
                    docket['consignor_address'] = '15, Madhav Complex, Nr. Bavla Sanand Chokdi'
                    docket['consignor_city'] = 'Bavla - 382220'
                    docket['consignor_phone'] = ''
                
                docket_pages.append(page_dockets)
            
            # Render HTML template
            html_content = render_template('pdf_template.html', docket_pages=docket_pages)
            
            # Generate PDF from HTML
            weasyprint.HTML(string=html_content).write_pdf(output_path)
            
            logger.info(f"PDF generated successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return False

# Initialize components
db_manager = DatabaseManager()

@app.route('/')
def index():
    """Main page"""
    missing_deps = check_dependencies()
    # Get current logo path
    logo_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith('logo.') and allowed_file(f)] if os.path.exists(UPLOAD_FOLDER) else []
    current_logo = logo_files[0] if logo_files else None
    
    return render_template('index.html', missing_dependencies=missing_deps, current_logo=current_logo)

@app.route('/upload-logo', methods=['POST'])
def upload_logo():
    """Handle logo upload"""
    if 'logo' not in request.files:
        flash('No logo file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['logo']
    if file.filename == '':
        flash('No logo file selected', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        # Remove existing logo files
        for existing_file in os.listdir(UPLOAD_FOLDER):
            if existing_file.startswith('logo.'):
                os.remove(os.path.join(UPLOAD_FOLDER, existing_file))
        
        # Save new logo
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        new_filename = f"logo.{file_extension}"
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        file.save(file_path)
        
        flash('Logo uploaded successfully!', 'success')
        logger.info(f"Logo uploaded: {file_path}")
    else:
        flash('Invalid file type. Please upload PNG, JPG, JPEG, GIF, or BMP files only.', 'error')
    
    return redirect(url_for('index'))

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

@app.route('/generate', methods=['POST'])
def generate_receipts():
    """Generate receipts PDF"""
    try:
        # Check dependencies first
        missing_deps = check_dependencies()
        if missing_deps:
            flash(f'Missing dependencies: {", ".join(missing_deps)}', 'error')
            return render_template('index.html', missing_dependencies=missing_deps)
        
        # Get logo path
        logo_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith('logo.') and allowed_file(f)] if os.path.exists(UPLOAD_FOLDER) else []
        logo_path = os.path.join(UPLOAD_FOLDER, logo_files[0]) if logo_files else None
        
        # Initialize PDF generator
        pdf_generator = PDFGenerator(logo_path=logo_path)
        
        # Get form data
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        party_code = request.form.get('party_code')
        
        if not start_date_str or not end_date_str:
            flash('Please provide both start and end dates', 'error')
            return render_template('index.html')
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Get data
        dockets = db_manager.get_dockets(start_date, end_date, party_code)
        
        if not dockets:
            flash('No dockets found for the selected criteria', 'warning')
            return render_template('index.html')
        
        parties = db_manager.get_parties()
        parties_map = {p['code']: p for p in parties}
        
        # Get party name for filename
        party_name = "All_Parties"
        if party_code:
            party_info = parties_map.get(party_code)
            if party_info:
                party_name = party_info['name'].replace(' ', '_').replace('/', '_')
        
        # Generate filename
        filename = f"Receipts_{party_name}_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.pdf"
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_path = temp_file.name
        temp_file.close()
        
        # Generate PDF
        success = pdf_generator.generate_pdf(dockets, parties_map, temp_path)
        
        if success:
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        else:
            flash('Error generating PDF', 'error')
            return render_template('index.html')
            
    except Exception as e:
        logger.error(f"Error in generate_receipts: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return render_template('index.html')

def cli_mode():
    """Command line interface mode"""
    print("\n=== Courier Receipt Generator - CLI Mode ===\n")
    
    # Check dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        print(f"Error: Missing dependencies: {', '.join(missing_deps)}")
        print("Please run install_py313.bat to install missing packages.")
        return
    
    # Initialize PDF generator
    try:
        logo_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith('logo.') and allowed_file(f)] if os.path.exists(UPLOAD_FOLDER) else []
        logo_path = os.path.join(UPLOAD_FOLDER, logo_files[0]) if logo_files else None
        pdf_generator = PDFGenerator(logo_path=logo_path)
    except ImportError as e:
        print(f"Error: {e}")
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
    
    # Get dockets
    print(f"\nSearching for dockets from {start_date} to {end_date}...")
    dockets = db_manager.get_dockets(start_date, end_date, party_code)
    
    if not dockets:
        print("No dockets found for the selected criteria.")
        return
    
    print(f"Found {len(dockets)} dockets.")
    confirm = input("Continue with PDF generation? (y/n): ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return
    
    # Generate PDF
    parties_map = {p['code']: p for p in parties}
    filename = f"Receipts_{party_name.replace(' ', '_').replace('/', '_')}_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.pdf"
    
    print(f"Generating PDF: {filename}")
    success = pdf_generator.generate_pdf(dockets, parties_map, filename)
    
    if success:
        print(f"PDF generated successfully: {filename}")
    else:
        print("Error generating PDF. Check logs for details.")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'cli':
        cli_mode()
    else:
        print("Starting web interface...")
        print("Open http://localhost:5000 in your browser")
        app.run(debug=True, host='0.0.0.0', port=5000)