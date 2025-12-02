import os
import secrets
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Security: Generate a random secret key if not provided
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_urlsafe(32)
    API_URL = os.getenv('API_URL')
    API_TOKEN = os.getenv('API_TOKEN')
    
    # Security: Session configuration - HARDENED
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'  # Force HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'  # Changed from Lax to Strict for maximum security
    SESSION_COOKIE_PATH = '/'
    SESSION_COOKIE_DOMAIN = os.getenv('SESSION_COOKIE_DOMAIN')  # Set domain in production
    PERMANENT_SESSION_LIFETIME = 1800  # Reduced to 30 minutes for security
    SESSION_REFRESH_EACH_REQUEST = True  # Refresh session on each request
    
    # Security: Debug should be False in production
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Security: Additional security headers
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year for static files
    
    # Security: Enhanced input validation limits
    MAX_BARCODE_LENGTH = 50
    MAX_SESSION_DURATION = 1800  # 30 minutes
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size
    MAX_FILENAME_LENGTH = 255
    MAX_USER_INPUT_LENGTH = 1000
    
    # Security: Rate limiting configuration - AGGRESSIVE LIMITS
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')  # Default to Redis
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STRATEGY = 'moving-window'  # More accurate than fixed-window
    RATELIMIT_DEFAULT = "100 per hour"  # Reduced default limit
    
    # Security: Enhanced rate limits per operation type
    RATELIMIT_SIGNIN = "10 per minute"  # Sign-in attempts
    RATELIMIT_ASSET_OPS = "30 per minute"  # Asset operations per user
    RATELIMIT_IMAGE_PROCESSING = "5 per minute"  # Image processing
    RATELIMIT_ADMIN_OPS = "20 per hour"  # Admin operations
    RATELIMIT_FILE_UPLOAD = "3 per minute"  # File uploads
    RATELIMIT_API_CALLS = "60 per minute"  # API calls per user
    
    # Security: Content Security Policy
    CSP_DEFAULT_SRC = "'self'"
    CSP_SCRIPT_SRC = "'self' 'unsafe-inline'"  # Minimize inline scripts in production
    CSP_STYLE_SRC = "'self' 'unsafe-inline'"
    CSP_IMG_SRC = "'self' data: blob:"
    CSP_CONNECT_SRC = "'self'"
    CSP_FONT_SRC = "'self'"
    CSP_OBJECT_SRC = "'none'"
    CSP_BASE_URI = "'self'"
    CSP_FORM_ACTION = "'self'"
    
    # Security: File upload restrictions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}  # Only image files for signatures
    FORBIDDEN_EXTENSIONS = {'exe', 'bat', 'sh', 'py', 'php', 'js', 'html', 'htm'}
    
    # Security: Logging configuration
    SECURITY_LOG_LEVEL = 'WARNING'
    MAX_LOG_SIZE = 100 * 1024 * 1024  # 100MB
    LOG_RETENTION_DAYS = 90
    
    # Security: API security
    API_TIMEOUT = 30  # 30 seconds timeout
    MAX_API_RETRIES = 3
    API_RATE_LIMIT = "120 per minute"  # API calls to external services
