from dbfread import DBF
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_parties():
    """Quick test to see what's in PRTMST.DBF"""
    try:
        # Try different encodings
        encodings = ['cp1252', 'cp850', 'cp437', 'latin1', 'utf-8']
        
        for encoding in encodings:
            try:
                print(f"\n=== Testing with encoding: {encoding} ===")
                prtmst = DBF('PRTMST.DBF', encoding=encoding)
                
                records = list(prtmst)
                print(f"Total records: {len(records)}")
                
                # Show first 5 records
                for i, record in enumerate(records[:5]):
                    print(f"Record {i+1}: {dict(record)}")
                
                # Count records with NAME field
                valid_parties = 0
                for record in records:
                    if record.get('NAME'):
                        valid_parties += 1
                
                print(f"Records with NAME field: {valid_parties}")
                
                # Show field structure
                prtmst = DBF('PRTMST.DBF', encoding=encoding)
                print(f"Fields: {[field.name for field in prtmst.fields]}")
                
                return encoding  # Success
                
            except Exception as e:
                print(f"Failed with {encoding}: {e}")
                continue
        
        print("No encoding worked!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_parties()