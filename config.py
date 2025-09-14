import os

class Config:
    """Application configuration"""
    
    # Database paths
    DLCHLN_PATH = os.environ.get('DLCHLN_PATH', 'DLCHLN.DBF')
    PRTMST_PATH = os.environ.get('PRTMST_PATH', 'PRTMST.DBF')
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # PDF configuration
    RECEIPTS_PER_PAGE = 4
    DEFAULT_ORIGIN = 'BAVLA'
    DEFAULT_SENDER = 'PHC - PRIMARY HEALTH CENTER - BAVLA'
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'courier_receipts.log')