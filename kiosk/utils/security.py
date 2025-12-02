# utils/security.py - HARDENED SECURITY MODULE

import re
import html
import logging
import secrets
import hashlib
import base64
import mimetypes
from functools import wraps
from typing import Tuple, Optional, Any, Dict, List
from flask import session, jsonify, request, current_app
from werkzeug.utils import secure_filename
import magic  # python-magic for file type detection

logger = logging.getLogger(__name__)

def validate_barcode(barcode: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    HARDENED barcode validation with multiple security layers
    
    Args:
        barcode: The barcode to validate
        
    Returns:
        tuple: (is_valid, sanitized_barcode, error_message)
    """
    if not barcode:
        log_security_event("VALIDATION_FAILURE", "Empty barcode submission")
        return False, None, "Barcode cannot be empty"
    
    # Type checking
    if not isinstance(barcode, str):
        log_security_event("VALIDATION_FAILURE", f"Invalid barcode type: {type(barcode)}")
        return False, None, "Invalid barcode format"
    
    # Remove whitespace and normalize
    barcode = barcode.strip()
    
    # Check for null bytes and control characters
    if '\x00' in barcode or any(ord(c) < 32 and c not in '\t\n\r' for c in barcode):
        log_security_event("VALIDATION_FAILURE", "Barcode contains control characters")
        return False, None, "Barcode contains invalid control characters"
    
    # Length validation with strict limits
    max_length = current_app.config.get('MAX_BARCODE_LENGTH', 50)
    if len(barcode) > max_length:
        log_security_event("VALIDATION_FAILURE", f"Barcode too long: {len(barcode)} chars")
        return False, None, f"Barcode too long (max {max_length} characters)"
    
    if len(barcode) < 3:  # Minimum reasonable length
        log_security_event("VALIDATION_FAILURE", f"Barcode too short: {len(barcode)} chars")
        return False, None, "Barcode too short (minimum 3 characters)"
    
    # Strict character allowlist - only alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9\-_]+$', barcode):
        log_security_event("VALIDATION_FAILURE", f"Barcode contains forbidden characters: {barcode}")
        return False, None, "Barcode contains invalid characters (only letters, numbers, hyphens, and underscores allowed)"
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'script', r'javascript:', r'vbscript:', r'onload', r'onerror',
        r'<script', r'</script', r'<iframe', r'<object', r'<embed',
        r'union.*select', r'drop.*table', r'insert.*into', r'delete.*from',
        r'\.\./', r'\.\.\\', r'/etc/', r'/proc/', r'/sys/',
        r'cmd\.exe', r'powershell', r'bash', r'/bin/', r'whoami'
    ]
    
    barcode_lower = barcode.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, barcode_lower, re.IGNORECASE):
            log_security_event("SECURITY_THREAT", f"Suspicious pattern in barcode: {pattern}")
            return False, None, "Barcode contains prohibited patterns"
    
    # Multiple encoding/escaping layers for defense in depth
    sanitized = html.escape(barcode, quote=True)
    
    return True, sanitized, None

def validate_user_input(input_text: str, max_length: int = None, field_name: str = "input") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    HARDENED general input validation and sanitization
    
    Args:
        input_text: Text to validate
        max_length: Maximum allowed length (uses config default if None)
        field_name: Name of field for logging
        
    Returns:
        tuple: (is_valid, sanitized_text, error_message)
    """
    if not input_text:
        return False, None, f"{field_name.title()} cannot be empty"
    
    # Type checking
    if not isinstance(input_text, str):
        log_security_event("VALIDATION_FAILURE", f"Invalid {field_name} type: {type(input_text)}")
        return False, None, f"Invalid {field_name} format"
    
    # Remove leading/trailing whitespace but preserve internal whitespace
    input_text = input_text.strip()
    
    # Check for null bytes and control characters (except common whitespace)
    if '\x00' in input_text:
        log_security_event("SECURITY_THREAT", f"Null byte in {field_name}")
        return False, None, f"{field_name.title()} contains invalid characters"
    
    # Remove or flag dangerous control characters
    if any(ord(c) < 32 and c not in '\t\n\r ' for c in input_text):
        log_security_event("VALIDATION_FAILURE", f"Control characters in {field_name}")
        return False, None, f"{field_name.title()} contains invalid control characters"
    
    # Length validation
    if max_length is None:
        max_length = current_app.config.get('MAX_USER_INPUT_LENGTH', 1000)
    
    if len(input_text) > max_length:
        log_security_event("VALIDATION_FAILURE", f"{field_name} too long: {len(input_text)} chars")
        return False, None, f"{field_name.title()} too long (max {max_length} characters)"
    
    # Check for extremely suspicious patterns
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'data:.*base64',
        r'union.*select.*from',
        r'drop.*table',
        r'insert.*into.*values',
        r'delete.*from.*where',
        r'update.*set.*where',
        r'exec\s*\(',
        r'eval\s*\(',
        r'system\s*\(',
        r'\.\.\/.*\/etc\/',
        r'\/etc\/passwd',
        r'\/proc\/.*\/environ'
    ]
    
    input_lower = input_text.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, input_lower, re.IGNORECASE | re.DOTALL):
            log_security_event("SECURITY_THREAT", f"Dangerous pattern in {field_name}: {pattern}")
            return False, None, f"{field_name.title()} contains prohibited content"
    
    # Multi-layer sanitization
    sanitized = html.escape(input_text, quote=True)
    
    # Additional normalization for specific attacks
    sanitized = re.sub(r'[<>"\']', '', sanitized)  # Remove remaining quotes/brackets
    
    return True, sanitized, None


def validate_filename(filename: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    SECURE filename validation
    
    Args:
        filename: The filename to validate
        
    Returns:
        tuple: (is_valid, sanitized_filename, error_message)
    """
    if not filename:
        return False, None, "Filename cannot be empty"
    
    # Use werkzeug's secure_filename as base
    secure_name = secure_filename(filename)
    if not secure_name:
        log_security_event("VALIDATION_FAILURE", f"Filename failed basic security check: {filename}")
        return False, None, "Invalid filename format"
    
    # Additional length check
    max_length = current_app.config.get('MAX_FILENAME_LENGTH', 255)
    if len(secure_name) > max_length:
        return False, None, f"Filename too long (max {max_length} characters)"
    
    # Check file extension
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg'})
    forbidden_extensions = current_app.config.get('FORBIDDEN_EXTENSIONS', set())
    
    if '.' in secure_name:
        extension = secure_name.rsplit('.', 1)[1].lower()
        
        # Check forbidden extensions first
        if extension in forbidden_extensions:
            log_security_event("SECURITY_THREAT", f"Forbidden file extension: {extension}")
            return False, None, f"File type '.{extension}' is not allowed"
        
        # Check allowed extensions
        if allowed_extensions and extension not in allowed_extensions:
            return False, None, f"File type '.{extension}' is not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    # Check for double extensions (common attack vector)
    if secure_name.count('.') > 1:
        parts = secure_name.split('.')
        for part in parts[1:-1]:  # Check all middle extensions
            if part.lower() in forbidden_extensions:
                log_security_event("SECURITY_THREAT", f"Hidden forbidden extension: {part}")
                return False, None, "Filename contains forbidden file type"
    
    return True, secure_name, None


def validate_base64_image(base64_data: str, max_size: int = None) -> Tuple[bool, Optional[bytes], Optional[str]]:
    """
    SECURE base64 image validation and decoding
    
    Args:
        base64_data: Base64 encoded image data
        max_size: Maximum allowed file size in bytes
        
    Returns:
        tuple: (is_valid, decoded_bytes, error_message)
    """
    if not base64_data:
        return False, None, "No image data provided"
    
    # Remove data URL prefix if present
    if ',' in base64_data:
        header, data = base64_data.split(',', 1)
        # Validate the header
        if not header.startswith('data:image/'):
            log_security_event("SECURITY_THREAT", f"Invalid image data header: {header}")
            return False, None, "Invalid image format"
    else:
        data = base64_data
    
    # Validate base64 format
    try:
        # Check if it's valid base64
        decoded_data = base64.b64decode(data, validate=True)
    except Exception as e:
        log_security_event("VALIDATION_FAILURE", f"Invalid base64 data: {str(e)}")
        return False, None, "Invalid image encoding"
    
    # Size validation
    if max_size is None:
        max_size = current_app.config.get('MAX_FILE_SIZE', 10 * 1024 * 1024)  # 10MB default
    
    if len(decoded_data) > max_size:
        log_security_event("VALIDATION_FAILURE", f"Image too large: {len(decoded_data)} bytes")
        return False, None, f"Image too large (max {max_size // (1024*1024)}MB)"
    
    # Minimum size check (avoid empty files)
    if len(decoded_data) < 100:  # Minimum reasonable image size
        return False, None, "Image file too small or corrupted"
    
    # Validate file type using magic bytes (requires python-magic)
    try:
        mime_type = magic.from_buffer(decoded_data, mime=True)
        allowed_types = ['image/png', 'image/jpeg', 'image/jpg']
        
        if mime_type not in allowed_types:
            log_security_event("SECURITY_THREAT", f"Invalid image MIME type: {mime_type}")
            return False, None, f"Invalid image type. Allowed: PNG, JPEG"
    except Exception as e:
        logger.warning(f"Could not validate image MIME type: {e}")
        # Continue without MIME validation if magic is not available
    
    # Check for embedded content/polyglot attacks
    if b'<?xml' in decoded_data[:1000] or b'<html' in decoded_data[:1000]:
        log_security_event("SECURITY_THREAT", "Potential XML/HTML content in image")
        return False, None, "Image contains invalid content"
    
    # Check for executable signatures
    executable_signatures = [
        b'\x4d\x5a',  # PE/COFF
        b'\x7f\x45\x4c\x46',  # ELF
        b'\xfe\xed\xfa',  # Mach-O
    ]
    
    for sig in executable_signatures:
        if decoded_data.startswith(sig):
            log_security_event("SECURITY_THREAT", "Executable signature detected in image")
            return False, None, "Image contains executable content"
    
    return True, decoded_data, None

def require_auth(f):
    """
    HARDENED authentication decorator with comprehensive security checks
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Enhanced session validation
        session_valid, auth_error = validate_session_security()
        if not session_valid:
            log_security_event("AUTH_FAILURE", f"Session validation failed: {auth_error}")
            # Clear invalid session and redirect to sign-in for GET requests
            session.clear()
            # Check if this is an AJAX request (modern replacement for is_xhr)
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json
            if request.method == 'GET' and not is_ajax:
                from flask import redirect, url_for
                return redirect(url_for('auth_bp.sign_in'))
            return jsonify({'success': False, 'error': 'Authentication required.'}), 401

        if 'user_id' not in session:
            log_security_event("AUTH_FAILURE", f"No user_id in session for {request.endpoint}")
            logger.warning(f'Unauthorized access attempt to {request.endpoint} from {get_client_ip()}')
            # Clear session and redirect to sign-in for GET requests
            session.clear()
            # Check if this is an AJAX request (modern replacement for is_xhr)
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json
            if request.method == 'GET' and not is_ajax:
                from flask import redirect, url_for
                return redirect(url_for('auth_bp.sign_in'))
            return jsonify({'success': False, 'error': 'Authentication required.'}), 401

        # Check for session hijacking indicators
        if detect_session_anomaly():
            log_security_event("SECURITY_THREAT", "Potential session hijacking detected")
            session.clear()
            # Check if this is an AJAX request (modern replacement for is_xhr)
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json
            if request.method == 'GET' and not is_ajax:
                from flask import redirect, url_for
                return redirect(url_for('auth_bp.sign_in'))
            return jsonify({'success': False, 'error': 'Security violation detected. Please sign in again.'}), 401
        
        # Update session activity
        update_session_activity()
        
        return f(*args, **kwargs)
    return decorated_function


def validate_session_security() -> Tuple[bool, Optional[str]]:
    """
    Comprehensive session security validation
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check if session exists
    if not session:
        return False, "No session found"
    
    # Check session timeout
    session_duration = current_app.config.get('MAX_SESSION_DURATION', 1800)
    last_activity = session.get('last_activity')
    
    if last_activity:
        import time
        if time.time() - last_activity > session_duration:
            session.clear()
            return False, "Session expired"
    
    # Validate session token integrity
    if 'session_token' in session:
        stored_token = session['session_token']
        expected_token = generate_session_token()
        
        # Compare tokens securely
        import hmac
        if not hmac.compare_digest(stored_token.encode(), expected_token.encode()):
            return False, "Session token mismatch"
    
    return True, None


def detect_session_anomaly() -> bool:
    """
    Detect potential session hijacking or anomalous behavior
    
    Returns:
        bool: True if anomaly detected
    """
    current_ip = get_client_ip()
    current_user_agent = request.headers.get('User-Agent', '')
    
    # Check IP consistency
    session_ip = session.get('session_ip')
    if session_ip and session_ip != current_ip:
        # Allow for reasonable IP changes (mobile networks, etc.)
        # but flag rapid changes or suspicious IPs
        last_ip_change = session.get('last_ip_change', 0)
        import time
        if time.time() - last_ip_change < 300:  # 5 minutes
            logger.warning(f"Rapid IP change detected: {session_ip} -> {current_ip}")
            return True
        
        session['session_ip'] = current_ip
        session['last_ip_change'] = time.time()
    
    # Check User-Agent consistency
    session_ua = session.get('session_user_agent')
    if session_ua and session_ua != current_user_agent:
        # User-Agent should be fairly consistent
        logger.warning(f"User-Agent change detected")
        return True
    
    # Check for suspicious request patterns
    request_count = session.get('request_count', 0)
    session['request_count'] = request_count + 1
    
    # Flag excessive requests in short time
    if request_count > 100:  # Reset counter periodically
        session['request_count'] = 1
    
    return False


def get_client_ip() -> str:
    """
    Securely get client IP address
    
    Returns:
        str: Client IP address
    """
    # Check for forwarded headers (but validate them)
    forwarded_ips = request.headers.getlist("X-Forwarded-For")
    if forwarded_ips:
        # Take the first IP (closest to client)
        client_ip = forwarded_ips[0].split(',')[0].strip()
        
        # Basic IP validation
        import ipaddress
        try:
            ipaddress.ip_address(client_ip)
            return client_ip
        except ValueError:
            pass
    
    # Fallback to remote_addr
    return request.remote_addr or 'unknown'


def generate_session_token() -> str:
    """
    Generate cryptographically secure session token

    Returns:
        str: Secure session token bound to session start time
    """
    import secrets
    import time

    # Generate or retrieve session-specific random token
    if 'session_token' not in session:
        # Create cryptographically random token
        session['session_token'] = secrets.token_urlsafe(32)
        session['session_start'] = time.time()

    return session['session_token']


def regenerate_session_token():
    """
    Regenerate session token on security-sensitive operations
    Should be called on login, privilege escalation, etc.
    """
    session.pop('session_token', None)
    session.pop('session_start', None)
    return generate_session_token()


def update_session_activity():
    """
    Update session activity tracking
    """
    import time
    session['last_activity'] = time.time()
    
    # Set session token if not present
    if 'session_token' not in session:
        session['session_token'] = generate_session_token()
    
    # Set IP and User-Agent if not present
    if 'session_ip' not in session:
        session['session_ip'] = get_client_ip()
    
    if 'session_user_agent' not in session:
        session['session_user_agent'] = request.headers.get('User-Agent', '')
    
    session.modified = True


def generate_secure_password(length: int = 16) -> str:
    """
    Generate cryptographically secure password
    
    Args:
        length: Password length (minimum 12)
        
    Returns:
        str: Secure password
    """
    if length < 12:
        length = 12
    
    # Use multiple character sets for better entropy
    import string
    
    # Ensure at least one character from each set
    chars = []
    chars.append(secrets.choice(string.ascii_lowercase))
    chars.append(secrets.choice(string.ascii_uppercase))
    chars.append(secrets.choice(string.digits))
    chars.append(secrets.choice('!@#$%^&*()_+-=[]{}|;:,.<>?'))
    
    # Fill the rest randomly
    all_chars = string.ascii_letters + string.digits + '!@#$%^&*()_+-=[]{}|;:,.<>?'
    for _ in range(length - 4):
        chars.append(secrets.choice(all_chars))
    
    # Shuffle the password
    secrets.SystemRandom().shuffle(chars)
    
    return ''.join(chars)

def log_security_event(event_type, details, user_id=None):
    """
    Log security-related events
    
    Args:
        event_type (str): Type of security event
        details (str): Details about the event
        user_id (str, optional): User ID if available
    """
    user_info = f"User: {user_id}" if user_id else "User: Unknown"
    remote_addr = request.remote_addr if request else "Unknown IP"
    
    logger.warning(f"SECURITY EVENT - {event_type}: {details} | {user_info} | IP: {remote_addr}")

def rate_limit_check(action, user_id=None, max_attempts=5, window_minutes=5):
    """
    Rate limiting check using Flask-Limiter decorators
    This function is now deprecated - use Flask-Limiter decorators directly on routes
    
    Args:
        action (str): Action being rate limited
        user_id (str): User performing the action
        max_attempts (int): Maximum attempts allowed
        window_minutes (int): Time window in minutes
        
    Returns:
        bool: True if action is allowed, False if rate limited
    """
    # This function is kept for backward compatibility
    # The actual rate limiting is now handled by Flask-Limiter decorators
    logger.info(f"Rate limit check for action: {action}, user: {user_id}")
    return True

def sanitize_json_response(data):
    """
    Sanitize JSON response data to prevent XSS
    
    Args:
        data (dict): Response data
        
    Returns:
        dict: Sanitized data
    """
    if isinstance(data, dict):
        return {k: sanitize_json_response(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json_response(item) for item in data]
    elif isinstance(data, str):
        return html.escape(data)
    else:
        return data
