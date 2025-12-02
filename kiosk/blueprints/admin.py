"""
Admin Blueprint
Handles administrative functions: user management, asset lookup, loan agreements, VIP access
"""
from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, current_app
import logging
from services.loan_agreement_service import loan_agreement_service
from utils.snipe_it_api import (
    check_user_vip_status,
    create_user,
    lookup_assets_by_user_name,
    lookup_asset_by_number,
    get_user_info_by_id,
    get_user_info,
    get_departments
)
from utils.security import (
    require_auth,
    log_security_event,
    generate_secure_password
)
from utils.csrf import csrf_protect

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)


def get_limiter():
    """Get the limiter instance from the current app"""
    return current_app.extensions.get('limiter')


def apply_rate_limit(limit_string, key_func=None, error_message="Too many requests. Please wait before trying again."):
    """
    Helper function to log rate limit checks

    Note: Actual rate limiting is handled by Flask-Limiter decorators and middleware
    This function is kept for logging and backwards compatibility
    """
    # Log rate limit check for monitoring
    logger.debug(f"Rate limit check requested: {limit_string}")
    # Flask-Limiter handles this automatically via decorators and middleware
    pass


@admin_bp.route('')
def admin():
    """Add User page for user management"""
    return render_template('admin.html')


@admin_bp.route('/asset-lookup-page')
@require_auth
def asset_lookup_page():
    """Asset lookup page for VIP users"""
    # Check if current user is VIP
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth_bp.sign_in'))

    user_info = get_user_info_by_id(user_id)
    if not user_info or not user_info.get('vip'):
        log_security_event("ADMIN_ACCESS_DENIED", f"Non-VIP user {user_id} attempted admin page access", user_id)
        return render_template('error.html', error="VIP access required"), 403

    return render_template('admin_lookup.html')


@admin_bp.route('/loan-agreement-page')
@require_auth
def loan_agreement_page():
    """Student Equipment/Accessories Loan Agreement Form for VIP users"""
    # Check if current user is VIP
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth_bp.sign_in'))

    user_info = get_user_info_by_id(user_id)
    if not user_info or not user_info.get('vip'):
        log_security_event("ADMIN_ACCESS_DENIED", f"Non-VIP user {user_id} attempted loan agreement page access", user_id)
        return render_template('error.html', error="VIP access required"), 403

    return render_template('loan_agreement.html', user_name=session.get('user_name', 'User'))


@admin_bp.route('/check-vip', methods=['POST'])
@require_auth
@csrf_protect
def check_vip():
    """Check if a user has VIP status"""
    apply_rate_limit("10 per minute")

    user_id = session.get('user_id')
    data = request.get_json()
    target_user_id = data.get('user_id')

    if not target_user_id:
        return jsonify({'success': False, 'error': 'User ID is required'}), 400

    success, is_vip = check_user_vip_status(target_user_id)

    if success:
        logger.info(f"VIP status check for user {target_user_id}: {is_vip}")
        return jsonify({'success': True, 'is_vip': is_vip})
    else:
        logger.error(f"Failed to check VIP status for user {target_user_id}")
        return jsonify({'success': False, 'error': 'Failed to check VIP status'})


@admin_bp.route('/clear-cache/<int:user_id>', methods=['POST'])
@require_auth
@csrf_protect
def clear_cache(user_id):
    """Clear user cache (placeholder for future caching implementation)"""
    apply_rate_limit("5 per minute")

    # Verify requestor is VIP
    requestor_id = session.get('user_id')
    requestor_info = get_user_info_by_id(requestor_id)

    if not requestor_info or not requestor_info.get('vip'):
        log_security_event("ADMIN_ACTION_DENIED", f"Non-VIP user {requestor_id} attempted cache clear", requestor_id)
        return jsonify({'success': False, 'error': 'VIP access required'}), 403

    logger.info(f"Cache clear requested for user {user_id} by VIP user {requestor_id}")
    log_security_event("ADMIN_CACHE_CLEAR", f"Cache cleared for user {user_id}", requestor_id)

    return jsonify({'success': True, 'message': 'Cache cleared successfully'})


@admin_bp.route('/asset-lookup', methods=['POST'])
@require_auth
@csrf_protect
def asset_lookup():
    """Look up assets by user name or asset number"""
    apply_rate_limit("10 per minute")

    # Check VIP status
    user_id = session.get('user_id')
    user_info = get_user_info_by_id(user_id)

    if not user_info or not user_info.get('vip'):
        log_security_event("ADMIN_LOOKUP_DENIED", f"Non-VIP user {user_id} attempted asset lookup", user_id)
        return jsonify({'success': False, 'error': 'VIP access required'}), 403

    data = request.get_json()
    search_query = data.get('search_query', '').strip()
    search_type = data.get('search_type', 'user_name')

    if not search_query:
        return jsonify({'success': False, 'error': 'Search query is required'}), 400

    logger.info(f"VIP user {user_info.get('name')} performing {search_type} lookup: {search_query}")

    if search_type == 'user_name':
        success, result = lookup_assets_by_user_name(search_query)
    elif search_type == 'asset_number':
        success, result = lookup_asset_by_number(search_query)
    else:
        return jsonify({'success': False, 'error': 'Invalid search type'}), 400

    if success:
        log_security_event("ADMIN_LOOKUP_SUCCESS", f"{search_type} lookup: {search_query}", user_id)
        return jsonify({'success': True, 'data': result})
    else:
        logger.warning(f"Lookup failed for {search_query}: {result}")
        return jsonify({'success': False, 'error': result})


@admin_bp.route('/lookup-student', methods=['POST'])
@require_auth
@csrf_protect
def lookup_student():
    """Look up student information for loan agreement"""
    apply_rate_limit("10 per minute")

    # Check VIP status
    user_id = session.get('user_id')
    user_info = get_user_info_by_id(user_id)

    if not user_info or not user_info.get('vip'):
        return jsonify({'success': False, 'error': 'VIP access required'}), 403

    data = request.get_json()
    student_id = data.get('employee_number', '').strip()

    if not student_id:
        return jsonify({'success': False, 'error': 'Student ID is required'}), 400

    logger.info(f"VIP user looking up student ID: {student_id}")

    # Look up student user by employee number (student ID)
    student_info = get_user_info(student_id)
    success = student_info is not None

    if success and student_info:
        return jsonify({
            'success': True,
            'student': {
                'id': student_info.get('id'),
                'name': student_info.get('name'),
                'email': student_info.get('email'),
                'department': student_info.get('department', {})
            }
        })
    else:
        return jsonify({'success': False, 'error': 'Student not found'})


@admin_bp.route('/create-student', methods=['POST'])
@require_auth
@csrf_protect
def create_student():
    """Create a new student user in Snipe-IT"""
    apply_rate_limit("5 per minute")

    # Check VIP status
    user_id = session.get('user_id')
    user_info = get_user_info_by_id(user_id)

    if not user_info or not user_info.get('vip'):
        return jsonify({'success': False, 'error': 'VIP access required'}), 403

    data = request.get_json()
    required_fields = ['first_name', 'last_name', 'email']

    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400

    student_data = {
        'first_name': data['first_name'].strip(),
        'last_name': data['last_name'].strip(),
        'email': data['email'].strip(),
        'username': data.get('username', data['email'].split('@')[0]).strip(),
        'employee_num': data.get('employee_num', '').strip()
    }

    logger.info(f"VIP user creating student: {student_data['email']}")

    success, result = create_user(student_data)

    if success:
        log_security_event("STUDENT_CREATED", f"Student created: {student_data['email']}", user_id)
        return jsonify({
            'success': True,
            'message': 'Student created successfully',
            'student_id': result.get('id')
        })
    else:
        logger.error(f"Failed to create student: {result}")
        return jsonify({'success': False, 'error': f'Failed to create student: {result}'})


@admin_bp.route('/validate-equipment', methods=['POST'])
@require_auth
@csrf_protect
def validate_equipment():
    """Validate equipment asset tags before loan agreement submission"""
    apply_rate_limit("10 per minute")

    # Check VIP status
    user_id = session.get('user_id')
    user_info = get_user_info_by_id(user_id)

    if not user_info or not user_info.get('vip'):
        return jsonify({'success': False, 'error': 'VIP access required'}), 403

    data = request.get_json()
    asset_tags = data.get('asset_tags', [])

    if not asset_tags:
        return jsonify({'success': False, 'error': 'No asset tags provided'}), 400

    from services.asset_service import asset_service

    validated_assets = []
    errors = []

    for asset_tag in asset_tags:
        success, result = asset_service.get_asset_info(asset_tag, user_id)
        if success:
            validated_assets.append({
                'asset_tag': asset_tag,
                'name': result.get('name'),
                'id': result.get('id'),
                'status': result.get('status_label', {}).get('name')
            })
        else:
            errors.append(f"{asset_tag}: {result}")

    return jsonify({
        'success': True,
        'validated': validated_assets,
        'errors': errors
    })


@admin_bp.route('/submit-loan-agreement', methods=['POST'])
@require_auth
@csrf_protect
def submit_loan_agreement():
    """Submit completed loan agreement form"""
    apply_rate_limit("5 per minute", error_message="Too many loan agreement submissions.")

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    user_id = session.get('user_id')
    success, result = loan_agreement_service.submit_loan_agreement(user_id, data)

    if success:
        return jsonify(result)
    else:
        return jsonify({'success': False, 'error': result.get('error', 'Unknown error')})


@admin_bp.route('/create-user', methods=['POST'])
@csrf_protect
def create_new_user():
    """Create a new user via admin interface"""
    apply_rate_limit("5 per hour", error_message="Too many user creation attempts.")

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No user data provided'})

    required_fields = ['first_name', 'last_name', 'username', 'email', 'employee_num']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'Missing required field: {field.replace("_", " ").title()}'})

    generated_password = generate_secure_password(16)

    user_data = {
        'first_name': data['first_name'].strip(),
        'last_name': data['last_name'].strip(),
        'username': data['username'].strip(),
        'email': data['email'].strip(),
        'employee_num': data['employee_num'].strip(),
        'password': generated_password,
        'vip': data.get('is_vip', False)
    }

    logger.info(f"Admin attempting to create user: {user_data['username']}")

    try:
        success, result = create_user(user_data)

        if success:
            log_security_event("ADMIN_USER_CREATED", f"Admin created user {user_data['username']} (Employee: {user_data['employee_num']})")
            return jsonify({
                'success': True,
                'message': f"User {user_data['username']} created successfully",
                'user_info': {
                    'username': user_data['username'],
                    'employee_num': user_data['employee_num'],
                    'is_vip': user_data['vip']
                }
            })
        else:
            logger.error(f"Failed to create user {user_data['username']}: {result}")
            return jsonify({'success': False, 'error': f'Failed to create user: {result}'})

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        log_security_event("ADMIN_USER_CREATION_ERROR", f"Error creating user {user_data.get('username', 'unknown')}: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while creating the user'})
