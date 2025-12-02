"""
Authentication Blueprint
Handles login, logout, and session management
"""
from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for
import logging
from utils.snipe_it_api import handle_user_signin
from utils.security import log_security_event

auth_bp = Blueprint('auth_bp', __name__)
logger = logging.getLogger(__name__)


@auth_bp.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
    """Login page and authentication handler"""
    if request.method == 'POST':
        # Handle barcode/employee ID sign-in
        data = request.get_json()
        barcode = data.get('barcode')

        if not barcode:
            return jsonify({'success': False, 'error': 'Employee ID is required'}), 400

        try:
            user_info = handle_user_signin(barcode)

            if user_info.get('error'):
                logger.error(f"Sign-in failed for barcode {barcode}: {user_info['error']}")
                log_security_event("AUTH_FAILURE", f"Sign-in failed: {user_info['error']}")
                return jsonify({'success': False, 'error': user_info['error']})

            # Save user session
            session['user_id'] = user_info['id']
            session['user_name'] = user_info['name']
            session['user_email'] = user_info.get('email', '')
            session['vip'] = user_info.get('vip', False)

            log_security_event("USER_LOGIN", f"User {user_info['name']} logged in", user_info['id'])
            logger.info(f"User signed in: {user_info['name']} (VIP: {session['vip']})")

            return jsonify({
                'success': True,
                'message': f"Welcome, {user_info['name']}!",
                'redirect': url_for('assets_bp.dashboard')
            })

        except Exception as e:
            logger.error(f"Sign-in error: {e}")
            log_security_event("AUTH_ERROR", f"Sign-in exception: {str(e)}")
            return jsonify({'success': False, 'error': 'Authentication failed. Please try again.'}), 500

    # GET request - show login page
    return render_template('sign_in.html')


@auth_bp.route('/test-session')
def test_session():
    """Test endpoint to check session status"""
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user_id': session['user_id'],
            'user_name': session.get('user_name', 'Unknown')
        })
    return jsonify({'logged_in': False})


@auth_bp.route('/logout')
def logout():
    """Log out current user"""
    user_name = session.get('user_name', 'Unknown')
    user_id = session.get('user_id')

    # Security: Log logout event
    log_security_event("USER_LOGOUT", f"User {user_name} logged out", user_id)
    logger.info(f"User logged out: {user_name}")

    # Security: Clear all session data including CSRF tokens
    # This invalidates CSRF tokens on logout per ITS security requirements
    session.clear()

    return redirect(url_for('auth_bp.sign_in'))
