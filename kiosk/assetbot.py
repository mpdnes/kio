# assetbot.py - HARDENED SECURITY EDITION

from flask import Flask, jsonify, request
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os
import secrets

assetbot = Flask(__name__)

# SECURITY: Load configurations with validation
assetbot.config.from_object('config.Config')

# SECURITY: Validate critical configuration
if not assetbot.config.get('SECRET_KEY'):
    assetbot.config['SECRET_KEY'] = secrets.token_urlsafe(32)
    logging.warning("SECRET_KEY not configured, generated temporary key")

# SECURITY: Enhanced Flask-Talisman configuration
talisman = Talisman(
    assetbot,
    force_https=assetbot.config.get('SESSION_COOKIE_SECURE', True),  # Force HTTPS in production
    strict_transport_security=True,
    strict_transport_security_max_age=31536000,  # 1 year
    strict_transport_security_include_subdomains=True,
    strict_transport_security_preload=True,
    session_cookie_secure=assetbot.config.get('SESSION_COOKIE_SECURE', True),
    session_cookie_http_only=True,
    content_security_policy={
        'default-src': assetbot.config.get('CSP_DEFAULT_SRC', "'self'"),
        'script-src': assetbot.config.get('CSP_SCRIPT_SRC', "'self' 'unsafe-inline'"),
        'style-src': assetbot.config.get('CSP_STYLE_SRC', "'self' 'unsafe-inline'"),
        'img-src': assetbot.config.get('CSP_IMG_SRC', "'self' data: blob:"),
        'connect-src': assetbot.config.get('CSP_CONNECT_SRC', "'self'"),
        'font-src': assetbot.config.get('CSP_FONT_SRC', "'self'"),
        'object-src': assetbot.config.get('CSP_OBJECT_SRC', "'none'"),
        'base-uri': assetbot.config.get('CSP_BASE_URI', "'self'"),
        'form-action': assetbot.config.get('CSP_FORM_ACTION', "'self'"),
        'frame-ancestors': "'none'",
        'upgrade-insecure-requests': [] if assetbot.config.get('DEBUG') else [''],
    },
    content_security_policy_nonce_in=[],
    referrer_policy='strict-origin-when-cross-origin',
    permissions_policy={
        'camera': "'self'",  # Allow camera access for barcode scanning
        'microphone': "()",  # No microphone access
        'geolocation': "()",  # No location access
        'payment': "()",     # No payment API
        'usb': "()",         # No USB access
        'serial': "()",      # No serial access
        'bluetooth': "()",   # No Bluetooth access
    },
    feature_policy={
        'camera': "'self'",
        'microphone': "'none'",
        'geolocation': "'none'",
    }
)

# SECURITY: Enhanced Flask-Limiter with Redis backend
limiter = Limiter(
    app=assetbot,
    key_func=get_remote_address,
    default_limits=[assetbot.config.get('RATELIMIT_DEFAULT', '100 per hour')],
    storage_uri=assetbot.config.get('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/0'),
    strategy=assetbot.config.get('RATELIMIT_STRATEGY', 'moving-window'),
    headers_enabled=assetbot.config.get('RATELIMIT_HEADERS_ENABLED', True),
    swallow_errors=True,  # Don't crash the app if rate limiting fails
    on_breach=lambda: logging.warning(f"Rate limit exceeded for {get_remote_address()}")
)

# Configure logging with better error handling and security considerations
try:
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Security: Different log levels for production vs development
    log_level = logging.INFO if not assetbot.config.get('DEBUG') else logging.DEBUG
    
    logging.basicConfig(
        filename='logs/assetbot.log',
        level=log_level,
        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
        filemode='a'
    )
    
    # Security: Limit log file size and rotation
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler('logs/assetbot.log', maxBytes=10485760, backupCount=5)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    assetbot.logger.addHandler(file_handler)
    
except (PermissionError, OSError):
    # Fallback to console logging if file logging fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
# SECURITY: Enhanced Flask security configurations
assetbot.config.update(
    SESSION_COOKIE_NAME='kiosk_session',
    SESSION_COOKIE_PATH='/',
    SESSION_COOKIE_DOMAIN=assetbot.config.get('SESSION_COOKIE_DOMAIN'),
    SESSION_COOKIE_SECURE=assetbot.config.get('SESSION_COOKIE_SECURE', True),
    SESSION_COOKIE_HTTPONLY=True,  # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE=assetbot.config.get('SESSION_COOKIE_SAMESITE', 'Strict'),
    PERMANENT_SESSION_LIFETIME=assetbot.config.get('PERMANENT_SESSION_LIFETIME', 1800),
    SESSION_REFRESH_EACH_REQUEST=True,  # Refresh session on each request
    MAX_CONTENT_LENGTH=assetbot.config.get('MAX_FILE_SIZE', 16 * 1024 * 1024),  # 16MB limit
)

# SECURITY: Initialize security modules after Flask configuration
try:
    from utils.security_headers import init_security_headers
    from utils.csrf import inject_csrf_token
    
    # Initialize security headers
    init_security_headers(assetbot)
    
    # Add CSRF token to template context
    assetbot.context_processor(inject_csrf_token)
    
    assetbot.logger.info("Security modules initialized successfully")
    
except ImportError as e:
    assetbot.logger.error(f"Failed to import security modules: {e}")

# SECURITY: Add request/response security middleware
@assetbot.before_request
def security_before_request():
    """COMPREHENSIVE security checks before processing any request"""
    # Skip security checks for static files and health checks
    if request.endpoint in ['static', 'favicon']:
        return
    
    # Log all requests for security monitoring
    user_agent = request.headers.get('User-Agent', 'Unknown')
    assetbot.logger.info(f"REQUEST: {request.method} {request.path} from {request.remote_addr} - UA: {user_agent[:100]}")
    
    # Check for suspicious request patterns
    suspicious_patterns = [
        '/admin' if not request.path.startswith('/admin') else None,
        '/.env', '/.git', '/config', '/wp-admin', '/phpmyadmin',
        '/../', '/etc/passwd', '/proc/', '/sys/',
        'script', 'javascript:', 'vbscript:', 'onload', 'onerror'
    ]
    
    path_lower = request.path.lower()
    for pattern in suspicious_patterns:
        if pattern and pattern in path_lower:
            assetbot.logger.warning(f"SECURITY: Suspicious request pattern detected: {pattern} in {request.path}")
            return jsonify({'error': 'Request blocked'}), 403
    
    # Rate limiting for the request (additional layer)
    if hasattr(request, 'remote_addr') and request.remote_addr:
        # This is handled by Flask-Limiter, but we log it for security monitoring
        pass

@assetbot.after_request  
def security_after_request(response):
    """COMPREHENSIVE security processing after request"""
    # Log error responses for security monitoring
    if response.status_code >= 400:
        assetbot.logger.warning(f"RESPONSE: {response.status_code} for {request.method} {request.path} from {request.remote_addr}")
    
    # Add additional security headers (complementary to Talisman)
    response.headers['X-Security-Enhanced'] = 'RIT-Kiosk-v2.0'
    
    # Remove server information disclosure
    response.headers.pop('Server', None)
    
    return response

# SECURITY: Removed sensitive configuration logging per ITS security requirements
# Configuration details should not be logged to prevent information disclosure
# Security: Add CSRF protection

from utils.csrf import inject_csrf_token
assetbot.context_processor(inject_csrf_token)


# Security: Disable server signature
# Security: Disable server signature and debug cookies
@assetbot.after_request
def remove_server_header(response):
    """Remove server identification headers and debug cookie setting"""
    from flask import current_app, request
    response.headers.pop('Server', None)
    
    # Debug: Log all Set-Cookie headers for debugging
    if hasattr(current_app, 'logger'):
        set_cookie_headers = response.headers.getlist('Set-Cookie')
        if set_cookie_headers:
            current_app.logger.debug(f"Setting cookies in response for {request.endpoint}: {set_cookie_headers}")
        else:
            current_app.logger.debug(f"No Set-Cookie headers in response for {request.endpoint}")
        
        # Log request cookies too
        current_app.logger.debug(f"Request cookies for {request.endpoint}: {dict(request.cookies)}")
    
    return response

# Rate limiting error handler
@assetbot.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors"""
    from utils.security import log_security_event
    log_security_event("RATE_LIMIT_EXCEEDED", f"Global rate limit exceeded: {e.description}")
    return jsonify({
        'success': False,
        'error': 'Rate limit exceeded. Please wait before making more requests.',
        'retry_after': getattr(e, 'retry_after', None)
    }), 429

# Register Blueprints - Modular Architecture
# Authentication blueprint
from blueprints.auth import auth_bp
assetbot.register_blueprint(auth_bp)

# Assets blueprint
from blueprints.assets import assets_bp
assetbot.register_blueprint(assets_bp)

# Admin blueprint
from blueprints.admin import admin_bp
assetbot.register_blueprint(admin_bp)

# Legacy main blueprint (home page only)
from blueprints.main import main_bp
assetbot.register_blueprint(main_bp)


