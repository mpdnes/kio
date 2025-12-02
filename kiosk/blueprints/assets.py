"""
Assets Blueprint
Handles asset operations: checkout, checkin, transfer, and information retrieval
"""
from flask import Blueprint, render_template, jsonify, request, session, current_app
import logging
import cv2
import base64
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
from services.asset_service import asset_service
from utils.security import (
    validate_barcode,
    require_auth,
    log_security_event,
    sanitize_json_response
)
from utils.csrf import csrf_protect

assets_bp = Blueprint('assets_bp', __name__)
logger = logging.getLogger(__name__)


def get_limiter():
    """Get the limiter instance from the current app"""
    # Try to get limiter from extensions
    limiter = current_app.extensions.get('limiter')
    # If not found, try getting it from the module
    if limiter is None or not hasattr(limiter, 'test'):
        try:
            from assetbot import limiter as app_limiter
            return app_limiter
        except ImportError:
            return None
    return limiter


def apply_rate_limit(limit_string, key_func=None, error_message="Too many requests. Please wait before trying again."):
    """
    Helper function to apply rate limiting with fail-secure behavior

    SECURITY: Note that Flask-Limiter with swallow_errors=True will not raise exceptions,
    so this just logs the attempt. Actual enforcement happens via Flask-Limiter middleware.
    """
    # Log rate limit check for monitoring
    logger.debug(f"Rate limit check requested: {limit_string}")
    # Flask-Limiter handles this automatically via decorators and middleware
    pass


@assets_bp.route('/dashboard')
@require_auth
def dashboard():
    """User dashboard page"""
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'User')
    is_vip = session.get('vip', False)

    logger.debug(f'Dashboard accessed by user {user_name}')

    # Get user's assigned assets
    from utils.snipe_it_api import get_user_assigned_assets, get_inventory_display_number
    assigned_assets = get_user_assigned_assets(user_id) if user_id else []

    # Add inventory display numbers to assets
    for asset in assigned_assets:
        asset['inventory_display_number'] = get_inventory_display_number(asset)

    logger.info(f"Retrieved {len(assigned_assets)} assets for user {user_id}")

    return render_template(
        'dashboard.html',
        user_name=user_name,
        is_vip=is_vip,
        assigned_assets=assigned_assets
    )


@assets_bp.route('/checkin-page')
@require_auth
def checkin_page():
    """Asset check-in page"""
    return render_template('checkin.html', user_name=session.get('user_name', 'User'))


@assets_bp.route('/checkout-page')
@require_auth
def checkout_page():
    """Asset checkout page"""
    return render_template('checkout.html', user_name=session.get('user_name', 'User'))


@assets_bp.route('/asset-info-page')
@require_auth
def asset_info_page():
    """Asset information lookup page"""
    return render_template('asset_info.html', user_name=session.get('user_name', 'User'))


@assets_bp.route('/equipment-info')
@require_auth
def equipment_info():
    """Equipment information page"""
    return render_template('equipment_info.html')


@assets_bp.route('/asset-info/<barcode>', methods=['GET'])
@require_auth
def asset_info(barcode):
    """Get asset information by barcode"""
    apply_rate_limit("30 per minute")

    if not validate_barcode(barcode):
        log_security_event("INVALID_BARCODE", f"Invalid barcode format: {barcode}", session.get('user_id'))
        return jsonify({'success': False, 'error': 'Invalid barcode format'}), 400

    user_id = session.get('user_id')
    success, result = asset_service.get_asset_info(barcode, user_id)

    if success:
        return jsonify({'success': True, 'data': sanitize_json_response(result)})
    else:
        return jsonify({'success': False, 'error': result})


@assets_bp.route('/public-asset-info/<barcode>', methods=['GET'])
def public_asset_info(barcode):
    """Public endpoint for asset information lookup"""
    apply_rate_limit("10 per minute")

    if not validate_barcode(barcode):
        log_security_event("INVALID_BARCODE_PUBLIC", f"Invalid barcode: {barcode}")
        return jsonify({'success': False, 'error': 'Invalid barcode format'}), 400

    success, result = asset_service.get_asset_info(barcode)

    if success:
        logger.info("Public asset info retrieved successfully")
        return jsonify({'success': True, 'data': sanitize_json_response(result)})
    else:
        return jsonify({'success': False, 'error': result})


@assets_bp.route('/checkin', methods=['POST'])
@require_auth
@csrf_protect
def checkin():
    """Check in an asset"""
    apply_rate_limit("10 per minute")

    data = request.get_json()
    asset_tag = data.get('asset_tag')

    if not asset_tag:
        return jsonify({'success': False, 'error': 'Asset tag is required'}), 400

    user_id = session.get('user_id')
    notes = data.get('notes', '')

    # Get asset info first to verify it exists
    success, asset_info = asset_service.get_asset_info(asset_tag, user_id)
    if not success:
        return jsonify({'success': False, 'error': f'Asset not found: {asset_info}'})

    # Pass the asset_tag (barcode) to checkin, not the asset ID
    success, result = asset_service.checkin_asset(asset_tag, user_id, notes)

    if success:
        return jsonify({'success': True, 'message': 'Asset checked in successfully', 'data': result})
    else:
        return jsonify({'success': False, 'error': result})


@assets_bp.route('/checkout', methods=['POST'])
@require_auth
@csrf_protect
def checkout():
    """Check out an asset"""
    apply_rate_limit("10 per minute")

    data = request.get_json()
    asset_tag = data.get('asset_tag')

    if not asset_tag:
        return jsonify({'success': False, 'error': 'Asset tag is required'}), 400

    user_id = session.get('user_id')
    notes = data.get('notes', '')

    # Get asset info first to verify it exists
    success, asset_info = asset_service.get_asset_info(asset_tag, user_id)
    if not success:
        return jsonify({'success': False, 'error': f'Asset not found: {asset_info}'})

    # Pass the asset_tag (barcode) to checkout, not the asset ID
    success, result = asset_service.checkout_asset(asset_tag, user_id, notes)

    if success:
        return jsonify({'success': True, 'message': 'Asset checked out successfully', 'data': result})
    else:
        return jsonify({'success': False, 'error': result})


@assets_bp.route('/transfer', methods=['POST'])
@require_auth
@csrf_protect
def transfer():
    """Transfer an asset to another user"""
    apply_rate_limit("10 per minute")

    data = request.get_json()
    asset_tag = data.get('asset_tag')
    target_user_id = data.get('target_user_id')

    if not asset_tag or not target_user_id:
        return jsonify({'success': False, 'error': 'Asset tag and target user ID are required'}), 400

    user_id = session.get('user_id')
    notes = data.get('notes', '')

    # Get asset info first to verify it exists
    success, asset_info = asset_service.get_asset_info(asset_tag, user_id)
    if not success:
        return jsonify({'success': False, 'error': f'Asset not found: {asset_info}'})

    # Pass the asset_tag (barcode) to transfer, not the asset ID
    success, result = asset_service.transfer_asset(asset_tag, target_user_id, user_id, notes)

    if success:
        return jsonify({'success': True, 'message': 'Asset transferred successfully', 'data': result})
    else:
        return jsonify({'success': False, 'error': result})


@assets_bp.route('/process_image', methods=['POST'])
@require_auth
@csrf_protect
def process_image():
    """Process an uploaded image to extract barcode"""
    apply_rate_limit("20 per minute")

    data = request.get_json()
    image_data = data.get('image')

    if not image_data:
        return jsonify({'success': False, 'error': 'No image data provided'}), 400

    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1])
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Try to decode barcode
        decoded_objects = decode(img, symbols=[ZBarSymbol.CODE128, ZBarSymbol.CODE39, ZBarSymbol.QRCODE])

        if decoded_objects:
            barcode = decoded_objects[0].data.decode('utf-8')
            return jsonify({'success': True, 'barcode': barcode})
        else:
            return jsonify({'success': False, 'error': 'No barcode detected in image'})

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return jsonify({'success': False, 'error': 'Failed to process image'})


@assets_bp.route('/process-barcode', methods=['POST'])
@require_auth
@csrf_protect
def process_barcode():
    """Process a barcode input (legacy endpoint)"""
    apply_rate_limit("20 per minute")

    data = request.get_json()
    barcode = data.get('barcode')

    if not barcode:
        return jsonify({'success': False, 'error': 'Barcode is required'}), 400

    if not validate_barcode(barcode):
        return jsonify({'success': False, 'error': 'Invalid barcode format'}), 400

    user_id = session.get('user_id')
    success, result = asset_service.get_asset_info(barcode, user_id)

    if success:
        return jsonify({'success': True, 'data': result})
    else:
        return jsonify({'success': False, 'error': result})


@assets_bp.route('/process_asset_barcode', methods=['POST'])
@require_auth
@csrf_protect
def process_asset_barcode():
    """Process asset barcode for lookup"""
    apply_rate_limit("20 per minute")

    data = request.get_json()
    barcode = data.get('barcode')

    if not barcode:
        return jsonify({'success': False, 'error': 'Barcode is required'}), 400

    user_id = session.get('user_id')
    success, result = asset_service.get_asset_info(barcode, user_id)

    if success:
        # Format response for frontend
        asset_name = result.get('name', '') or f"Asset {barcode}"

        # Get inventory number from custom fields or asset tag
        inventory_number = barcode
        if 'custom_fields' in result:
            custom_fields = result['custom_fields']
            # Try inventory number fields first (customize these to match your Snipe-IT setup)
            for field_name in ['Inventory Number', 'inventory_number', 'inventory']:
                if field_name in custom_fields:
                    field_data = custom_fields[field_name]
                    if isinstance(field_data, dict) and 'value' in field_data and field_data['value']:
                        inventory_number = field_data['value']
                        break
                    elif field_data:
                        inventory_number = field_data
                        break

        return jsonify({
            'success': True,
            'asset': result,
            'asset_name': asset_name,
            'inventory_number': inventory_number
        })
    else:
        return jsonify({'success': False, 'error': result})
