# utils/security_headers.py - COMPREHENSIVE SECURITY HEADERS MODULE

from flask import current_app, request
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def add_security_headers(response):
    """
    Add comprehensive security headers to all responses
    
    Args:
        response: Flask response object
        
    Returns:
        response: Modified response with security headers
    """
    
    # Content Security Policy (CSP) - STRICT
    default_src = current_app.config.get('CSP_DEFAULT_SRC', "'self'")
    script_src = current_app.config.get('CSP_SCRIPT_SRC', "'self'")
    style_src = current_app.config.get('CSP_STYLE_SRC', "'self' 'unsafe-inline'")
    img_src = current_app.config.get('CSP_IMG_SRC', "'self' data: blob:")
    connect_src = current_app.config.get('CSP_CONNECT_SRC', "'self'")
    font_src = current_app.config.get('CSP_FONT_SRC', "'self'")
    object_src = current_app.config.get('CSP_OBJECT_SRC', "'none'")
    base_uri = current_app.config.get('CSP_BASE_URI', "'self'")
    form_action = current_app.config.get('CSP_FORM_ACTION', "'self'")
    
    csp_directives = [
        f"default-src {default_src}",
        f"script-src {script_src}",
        f"style-src {style_src}",
        f"img-src {img_src}",
        f"connect-src {connect_src}",
        f"font-src {font_src}",
        f"object-src {object_src}",
        f"base-uri {base_uri}",
        f"form-action {form_action}",
        "frame-ancestors 'none'",  # Prevent framing
        "upgrade-insecure-requests",  # Force HTTPS
    ]
    
    csp_policy = "; ".join(csp_directives)
    response.headers['Content-Security-Policy'] = csp_policy
    
    # Strict Transport Security (HSTS) - Force HTTPS for 1 year
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    # X-Content-Type-Options - Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # X-Frame-Options - Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # X-XSS-Protection - Enable XSS filtering
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer Policy - Control referrer information
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions Policy (formerly Feature Policy)
    permissions_policy = [
        "camera=('self')",  # Allow camera for barcode scanning
        "microphone=()",    # No microphone access
        "geolocation=()",   # No location access
        "payment=()",       # No payment API
        "usb=()",          # No USB access
        "serial=()",       # No serial port access
        "bluetooth=()",    # No Bluetooth access
        "magnetometer=()", # No magnetometer
        "gyroscope=()",    # No gyroscope
        "accelerometer=()" # No accelerometer
    ]
    response.headers['Permissions-Policy'] = ", ".join(permissions_policy)
    
    # Clear-Site-Data - Clear browser data on logout (if applicable)
    if request.endpoint and 'logout' in request.endpoint:
        response.headers['Clear-Site-Data'] = '"cache", "cookies", "storage", "executionContexts"'
    
    # X-Permitted-Cross-Domain-Policies - Restrict cross-domain policies
    response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
    
    # X-DNS-Prefetch-Control - Disable DNS prefetching
    response.headers['X-DNS-Prefetch-Control'] = 'off'
    
    # Cross-Origin Policies
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    
    # Cache Control for sensitive pages
    if request.endpoint and any(sensitive in request.endpoint for sensitive in ['dashboard', 'admin', 'asset']):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    # Server header removal (security through obscurity)
    response.headers.pop('Server', None)
    
    # Custom security headers
    response.headers['X-Security-Policy'] = 'RIT-Kiosk-Hardened'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow, nosnippet, noarchive'
    
    return response


def require_https():
    """
    Decorator to require HTTPS for sensitive endpoints
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_secure and not current_app.config.get('DEBUG', False):
                logger.warning(f"HTTP access attempt to secure endpoint: {request.endpoint}")
                return {
                    'error': 'HTTPS required for this endpoint',
                    'redirect': request.url.replace('http://', 'https://', 1)
                }, 426  # Upgrade Required
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_request_headers():
    """
    Validate incoming request headers for security threats
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check for suspicious headers
    suspicious_headers = [
        'X-Forwarded-Host',  # Potential host header injection
        'X-Original-Host',
        'X-Rewrite-Url'
    ]
    
    for header in suspicious_headers:
        if header in request.headers:
            logger.warning(f"Suspicious header detected: {header}")
            return False, f"Suspicious request header: {header}"
    
    # Validate Host header
    host_header = request.headers.get('Host')
    allowed_hosts = current_app.config.get('ALLOWED_HOSTS', [])
    
    if allowed_hosts and host_header not in allowed_hosts:
        logger.warning(f"Invalid Host header: {host_header}")
        return False, "Invalid Host header"
    
    # Check Content-Length for potential attacks
    content_length = request.headers.get('Content-Length')
    if content_length:
        try:
            length = int(content_length)
            max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)  # 16MB
            if length > max_size:
                return False, "Request too large"
        except ValueError:
            return False, "Invalid Content-Length header"
    
    # Validate User-Agent (basic check)
    user_agent = request.headers.get('User-Agent', '')
    if len(user_agent) > 500:  # Unusually long user agent
        logger.warning(f"Suspiciously long User-Agent: {len(user_agent)} chars")
        return False, "Invalid User-Agent"
    
    # Check for null bytes in headers
    for header_name, header_value in request.headers:
        if '\x00' in header_value:
            logger.warning(f"Null byte in header {header_name}")
            return False, "Invalid header content"
    
    return True, None


class SecurityHeadersMiddleware:
    """
    WSGI middleware for adding security headers to all responses
    """
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        def new_start_response(status, response_headers):
            # Add security headers
            security_headers = [
                ('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload'),
                ('X-Content-Type-Options', 'nosniff'),
                ('X-Frame-Options', 'DENY'),
                ('X-XSS-Protection', '1; mode=block'),
                ('Referrer-Policy', 'strict-origin-when-cross-origin'),
                ('X-Permitted-Cross-Domain-Policies', 'none'),
                ('X-DNS-Prefetch-Control', 'off'),
            ]
            
            # Remove server header
            response_headers = [(name, value) for name, value in response_headers if name.lower() != 'server']
            
            # Add security headers
            response_headers.extend(security_headers)
            
            return start_response(status, response_headers)
        
        return self.app(environ, new_start_response)


def init_security_headers(app):
    """
    Initialize security headers for the Flask app
    
    Args:
        app: Flask application instance
    """
    
    @app.after_request
    def add_security_headers_to_response(response):
        return add_security_headers(response)
    
    @app.before_request
    def validate_request():
        # Skip validation for static files
        if request.endpoint == 'static':
            return
        
        is_valid, error = validate_request_headers()
        if not is_valid:
            logger.warning(f"Request validation failed: {error}")
            return {'error': 'Invalid request'}, 400
    
    logger.info("Security headers middleware initialized")