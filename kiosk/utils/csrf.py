# utils/csrf.py - Simple CSRF Protection

import secrets
import hmac
import hashlib
import time
from flask import session, request, jsonify
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def generate_csrf_token():
    """Generate a CSRF token for the current session"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
        session['csrf_timestamp'] = time.time()
    return session['csrf_token']

def validate_csrf_token(token):
    """Validate a CSRF token"""
    if not token:
        return False
    
    session_token = session.get('csrf_token')
    if not session_token:
        return False
    
    # Check token age (expire after 1 hour)
    timestamp = session.get('csrf_timestamp', 0)
    if time.time() - timestamp > 3600:  # 1 hour
        session.pop('csrf_token', None)
        session.pop('csrf_timestamp', None)
        return False
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(session_token, token)

def csrf_protect(f):
    """Decorator to protect routes with CSRF validation"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Get token from header or form data
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            
            if not validate_csrf_token(token):
                logger.warning(f'CSRF validation failed for {request.endpoint} from {request.remote_addr}')
                return jsonify({'success': False, 'error': 'CSRF token validation failed.'}), 403
                
        return f(*args, **kwargs)
    return decorated_function

def inject_csrf_token():
    """Template context processor to inject CSRF token"""
    return dict(csrf_token=generate_csrf_token())
