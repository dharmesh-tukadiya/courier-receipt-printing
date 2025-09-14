import os
import sys
from dbfread import DBF

def debug_dbf_file(file_path):
    """Debug DBF file to understand its structure and encoding"""
    print(f"\n=== Debugging {file_path} ===")
    
    if not os.path.exists(file_path):
        print(f"ERROR: File {file_path} not found!")
        return
    
    # File info
    file_size = os.path.getsize(file_path)
    print(f"File size: {file_size} bytes")
    
    # Try different encodings
    encodings = ['cp1252', 'cp850', 'cp437', 'latin1', 'utf-8']
    
    for encoding in encodings:
        try:
            print(f"\nTrying encoding: {encoding}")
            dbf = DBF(file_path, encoding=encoding)
            
            print(f"  Records: {len(list(dbf))}")
            print(f"  Fields: {[field.name for field in dbf.fields]}")
            
            # Read first few records
            dbf = DBF(file_path, encoding=encoding)
            for i, record in enumerate(dbf):
                if i >= 3:  # Show first 3 records
                    break
                print(f"  Record {i+1}: {dict(record)}")
            
            print(f"SUCCESS with {encoding}")
            return encoding
            
        except Exception as e:
            print(f"  FAILED: {str(e)}")
    
    print("Could not read file with any encoding!")
    return None

if __name__ == '__main__':
    debug_dbf_file('DLCHLN.DBF')
    debug_dbf_file('PRTMST.DBF')