# utils/snipe_it_api.py

import requests
import logging
from flask import current_app
from utils.security import log_security_event, sanitize_json_response

logger = logging.getLogger(__name__)

def get_inventory_display_number(asset):
    """
    Get the appropriate inventory number for display.
    Falls back to asset_tag if no custom fields are available.
    Customize the field names to match your organization's Snipe-IT setup.
    """
    if not asset:
        return "N/A"
    
    # Debug logging for all assets
    name = asset.get('name', '').lower()
    asset_tag = asset.get('asset_tag', 'Unknown')
    model_name = asset.get('model', {}).get('name', '').lower()
    category_name = asset.get('category', {}).get('name', '').lower()
    asset_type = "Unknown"
    
    # Enhanced asset type detection using name, model, and category
    if 'ipad' in name or 'tablet' in name or 'ipad' in model_name:
        asset_type = "iPad"
    elif ('microphone' in name or 'mic' in name or 
          'microphone' in model_name or 'mic' in model_name or 
          'microphone' in category_name):
        asset_type = "Microphone"
    elif not name.strip():  # Empty or whitespace-only name
        asset_type = "Unnamed Asset"
    else:
        asset_type = "Other"
    
    logger.info(f"DEBUG: Processing {asset_type} asset - Name: '{asset.get('name')}', Tag: {asset_tag}")
    logger.info(f"DEBUG: Custom fields available: {list(asset.get('custom_fields', {}).keys())}")
    
    # Check for custom fields first
    custom_fields = asset.get('custom_fields', {})
    
    # For iPads and Microphones, look for custom inventory number fields
    # Customize these field names to match your Snipe-IT custom fields
    if asset_type in ["iPad", "Microphone"]:
        # Look for inventory number - check the actual field names as they appear in Snipe-IT
        inventory_fields = [
            'Inventory Number',  # Generic field name
            'inventory_number', 'inventory', 'item_number'  # Fallback names
        ]
        for field in inventory_fields:
            if field in custom_fields:
                field_data = custom_fields[field]
                # Custom fields are stored as objects with 'value' property
                if isinstance(field_data, dict) and 'value' in field_data and field_data['value']:
                    logger.info(f"DEBUG: Found inventory field '{field}' with value: {field_data['value']}")
                    return str(field_data['value'])
                elif field_data:  # Simple string value
                    logger.info(f"DEBUG: Found inventory field '{field}' with value: {field_data}")
                    return str(field_data)
        
        # If no inventory fields found, log what's available
        logger.info(f"DEBUG: No inventory fields found for {asset_type}. Available custom fields: {list(custom_fields.keys())}")
        # For tablets, check if there's a serial number or other identifier
        if asset_type == "iPad":
            if 'serial' in custom_fields and custom_fields['serial']:
                logger.info(f"DEBUG: Using serial number: {custom_fields['serial']}")
                return str(custom_fields['serial'])
    
    # For other items, look for custom inventory fields
    other_inventory_fields = [
        'Inventory Number',  # Generic field name
        'inventory_number', 'inventory', 'item_number'
    ]
    for field in other_inventory_fields:
        if field in custom_fields:
            field_data = custom_fields[field]
            # Custom fields are stored as objects with 'value' property
            if isinstance(field_data, dict) and 'value' in field_data and field_data['value']:
                logger.info(f"DEBUG: Found inventory field '{field}' with value: {field_data['value']}")
                return str(field_data['value'])
            elif field_data:  # Simple string value
                logger.info(f"DEBUG: Found inventory field '{field}' with value: {field_data}")
                return str(field_data)
    
    # Check for serial number as backup
    serial = asset.get('serial')
    if serial:
        return f"S/N: {serial}"
    
    # Fall back to asset tag
    return asset.get('asset_tag', 'N/A')

def get_api_headers():
    """Get API headers with proper authorization"""
    token = current_app.config.get("API_TOKEN")
    if not token:
        logger.error("API_TOKEN not configured")
        raise ValueError("API configuration missing")
    
    return {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

def make_api_request(method, endpoint, **kwargs):
    """
    Make a secure API request with proper error handling
    
    Args:
        method (str): HTTP method (GET, POST, etc.)
        endpoint (str): API endpoint
        **kwargs: Additional arguments for requests
        
    Returns:
        tuple: (success, data_or_error_message)
    """
    api_url = current_app.config.get('API_URL')
    if not api_url:
        logger.error("API_URL not configured")
        return False, "API configuration missing"
    
    headers = get_api_headers()
    url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"

    # SECURITY: SSL verification ALWAYS enabled for production security
    # Removed VERIFY_SSL config option to prevent MITM attacks
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            verify=True,  # Always verify SSL certificates
            timeout=30,  # Add timeout to prevent hanging requests
            **kwargs
        )
        response.raise_for_status()
        
        # Log successful API calls at debug level
        logger.debug(f"API {method} {endpoint} - Status: {response.status_code}")
        
        return True, response.json()
        
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL Error in API request to {endpoint}: {e}")
        log_security_event("API_SSL_ERROR", f"SSL error accessing {endpoint}")
        return False, "SSL connection error. Please check your network configuration."
        
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout in API request to {endpoint}: {e}")
        return False, "Request timeout. Please try again."
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error in API request to {endpoint}: {e}")
        return False, "Unable to connect to the asset management system."
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error in API request to {endpoint}: {e}")
        if response.status_code == 401:
            log_security_event("API_AUTH_FAILURE", f"Authentication failed for {endpoint}")
            return False, "Authentication failed. Please contact system administrator."
        elif response.status_code == 403:
            log_security_event("API_PERMISSION_DENIED", f"Permission denied for {endpoint}")
            return False, "Permission denied."
        elif response.status_code == 404:
            return False, "Resource not found."
        else:
            return False, f"Server error ({response.status_code}). Please try again."
            
    except requests.RequestException as e:
        logger.error(f"Request error in API request to {endpoint}: {e}")
        return False, "An error occurred while communicating with the asset management system."
        
    except Exception as e:
        logger.error(f"Unexpected error in API request to {endpoint}: {e}")
        return False, "An unexpected error occurred. Please try again."

def get_user_info(employee_num):
    """Fetches the user information from Snipe-IT using the employee number."""
    if not employee_num or not str(employee_num).strip():
        return None
    
    success, data = make_api_request('GET', '/users', params={'search': str(employee_num).strip()})
    
    if not success:
        logger.error(f"Failed to fetch user info: {data}")
        return None
    
    # Check if there are any matching users
    if 'rows' in data and len(data['rows']) > 0:
        logger.debug(f"Found user with employee number: {employee_num}")
        user_data = data['rows'][0]
        return sanitize_json_response(user_data)
    else:
        logger.warning(f"No user found for employee number: {employee_num}")
        return None

def handle_user_signin(barcode_data):
    """Handles user sign-in by scanning a barcode."""
    if not barcode_data:
        return {'error': "Invalid barcode data."}
    
    # Security: Log sign-in attempt
    log_security_event("USER_SIGNIN_ATTEMPT", f"Sign-in attempt with barcode data")
    
    user_info = get_user_info(employee_num=barcode_data)
    if user_info:
        log_security_event("USER_SIGNIN_SUCCESS", f"Successful sign-in for user ID: {user_info.get('id')}")
        return {
            'id': user_info['id'],
            'name': user_info['name'],
            'employee_num': user_info.get('employee_num'),
            'vip': user_info.get('vip', False),
            'email': user_info.get('email', '')
        }
    else:
        log_security_event("USER_SIGNIN_FAILURE", f"Failed sign-in attempt")
        return {'error': "Failed to sign in. User not found."}

def extract_asset_id_from_barcode(barcode_data):
    """Extracts the asset ID from the barcode data."""
    # Security: This should include validation
    from utils.security import validate_barcode
    
    is_valid, sanitized_barcode, error = validate_barcode(barcode_data)
    if not is_valid:
        raise ValueError(f"Invalid barcode: {error}")
    
    return sanitized_barcode

def get_asset_info(asset_identifier):
    """Fetches the asset information from Snipe-IT."""
    if not asset_identifier:
        return None
    
    try:
        sanitized_identifier = extract_asset_id_from_barcode(asset_identifier)
    except ValueError as e:
        logger.error(f"Invalid asset identifier: {e}")
        return None
    
    success, data = make_api_request('GET', '/hardware', params={'search': sanitized_identifier})
    
    if not success:
        logger.error(f"Failed to fetch asset info: {data}")
        return None
    
    if 'rows' in data and len(data['rows']) > 0:
        asset_data = data['rows'][0]
        
        # Debug logging to help identify assignment issues
        logger.debug(f"Asset {sanitized_identifier} info: status={asset_data.get('status_label', {}).get('name')}, "
                    f"assigned_to={asset_data.get('assigned_to', {}).get('name') if asset_data.get('assigned_to') else 'None'}")
        
        return sanitize_json_response(asset_data)
    else:
        logger.warning(f"No asset found for identifier: {sanitized_identifier}")
        return None

def is_asset_checked_out(asset_info):
    """Checks if the asset is currently checked out."""
    if not asset_info:
        return False
    
    # Check if asset is assigned to someone (primary indicator of being checked out)
    if asset_info.get('assigned_to'):
        return True
    
    # Fallback: check status_meta if available
    if asset_info.get('status_label', {}).get('status_meta') == 'deployed':
        return True
        
    # Additional fallback: check if status is "Checked out" (ID 4)
    if asset_info.get('status_label', {}).get('id') == 4:
        return True
        
    return False

def is_asset_assigned_to_user(asset_info, user_id):
    """Checks if the asset is currently assigned to the given user."""
    if not asset_info or not user_id:
        return False
    
    assigned_user = asset_info.get('assigned_to')
    if assigned_user and assigned_user.get('id') == int(user_id):
        return True
    else:
        return False

def checkout_asset(barcode_data, user_id):
    """Handles asset checkout."""
    if not barcode_data or not user_id:
        return {'error': "Missing required parameters."}
    
    try:
        asset_id = extract_asset_id_from_barcode(barcode_data)
    except ValueError as e:
        return {'error': str(e)}
      # Check if asset exists and is available
    asset_info = get_asset_info(asset_id)
    if not asset_info:
        return {'error': "Asset not found."}

    if is_asset_checked_out(asset_info):
        # Check if already assigned to the same user
        if is_asset_assigned_to_user(asset_info, user_id):
            return {'error': "Asset is already checked out to you."}
        else:
            assigned_user = asset_info.get('assigned_to', {})
            assigned_name = assigned_user.get('name', 'another user')
            assigned_id = assigned_user.get('id')
            return {
                'error': f"Asset is already checked out to {assigned_name}.",
                'transfer_available': True,
                'current_user': assigned_name,
                'current_user_id': assigned_id,
                'asset_name': asset_info.get('name') or asset_info.get('model', {}).get('name', f"Asset {asset_info.get('asset_tag')}")
            }

    # Use the correct required parameters according to Snipe-IT API documentation
    # Status ID 7 might be the correct "Deployed" status for this instance
    payload = {
        "status_id": 2,  # Use Status ID 2 (Ready to Deploy) - this is what worked before
        "checkout_to_type": "user",  # Required
        "assigned_user": int(user_id),  # Required when checkout_to_type is "user"
        "note": "Checked out via kiosk"
    }

    logger.debug(f"Attempting checkout with payload: {payload}")
    
    success, data = make_api_request(
        'POST', 
        f"/hardware/{asset_info['id']}/checkout",
        json=payload
    )
    
    logger.debug(f"Checkout API response - Success: {success}, Data: {data}")
    
    if success:
        log_security_event("ASSET_CHECKOUT", f"Asset {asset_id} checked out to user {user_id}", user_id)
        logger.info(f"Asset {asset_id} checkout API call succeeded")
        
        # Wait a moment and check the result
        import time
        time.sleep(2.0)  # Give it more time
        
        updated_asset_info = get_asset_info(asset_id)
        logger.debug(f"Asset info after checkout: assigned_to={updated_asset_info.get('assigned_to') if updated_asset_info else None}")
        
        # Debug: Log the full asset status after checkout
        if updated_asset_info:
            assigned_to = updated_asset_info.get('assigned_to', {})
            assigned_to_id = assigned_to.get('id') if assigned_to else None
            status = updated_asset_info.get('status_label', {}).get('name', 'Unknown')
            logger.info(f"DEBUG: Post-checkout asset state - Status: {status}, Assigned to ID: {assigned_to_id}, User ID: {user_id}")
        
        if updated_asset_info and is_asset_assigned_to_user(updated_asset_info, user_id):
            logger.info(f"Asset {asset_id} successfully assigned to user {user_id}")
            
            # Create enhanced checkout message with asset name and inventory number
            asset_name = updated_asset_info.get('name')
            if not asset_name:
                # Use model name for unnamed assets (like microphones)
                model_name = updated_asset_info.get('model', {}).get('name')
                if model_name:
                    asset_name = model_name
                else:
                    asset_name = f"Asset {updated_asset_info.get('asset_tag')}"
            
            inventory_number = get_inventory_display_number(updated_asset_info)
            
            if inventory_number and inventory_number != updated_asset_info.get('asset_tag'):
                checkout_message = f"Successfully checked out: {asset_name} (Inventory: {inventory_number})"
            else:
                checkout_message = f"Successfully checked out: {asset_name} (Tag: {updated_asset_info.get('asset_tag')})"
            
            return {
                'message': checkout_message,
                'asset_info': updated_asset_info
            }
        else:
            # Log detailed info about what we got back
            if updated_asset_info:
                status = updated_asset_info.get('status_label', {})
                assigned = updated_asset_info.get('assigned_to')
                assigned_name = assigned.get('name') if assigned else None
                assigned_id = assigned.get('id') if assigned else None
                logger.warning(f"Asset {asset_id} checkout issue - Status: {status.get('name')}, Assigned to: {assigned_name} (ID: {assigned_id}), Expected user: {user_id}")
                
                # Fix: If asset is still in "Ready to Deploy" but should be assigned, force update to "Checked out"
                if status.get('id') == 2 and not assigned:
                    logger.info(f"Forcing status update for asset {asset_id} to 'Checked out' with assignment")
                    fix_payload = {
                        'status_id': 4,  # Checked out status
                        'assigned_to': int(user_id)
                    }
                    fix_success, fix_response = make_api_request('PATCH', f'/hardware/{asset_info.get("id")}', json=fix_payload)
                    
                    if fix_success:
                        logger.info(f"Successfully forced update for asset {asset_id}")
                        # Get updated info
                        time.sleep(1)
                        final_asset_info = get_asset_info(asset_id)
                        if final_asset_info and is_asset_assigned_to_user(final_asset_info, user_id):
                            # Create enhanced message for corrected checkout
                            asset_name = final_asset_info.get('name')
                            if not asset_name:
                                # Use model name for unnamed assets (like microphones)
                                model_name = final_asset_info.get('model', {}).get('name')
                                if model_name:
                                    asset_name = model_name
                                else:
                                    asset_name = f"Asset {final_asset_info.get('asset_tag')}"
                            
                            inventory_number = get_inventory_display_number(final_asset_info)
                            
                            if inventory_number and inventory_number != final_asset_info.get('asset_tag'):
                                corrected_message = f"Successfully checked out: {asset_name} (Inventory: {inventory_number}) - Status corrected"
                            else:
                                corrected_message = f"Successfully checked out: {asset_name} (Tag: {final_asset_info.get('asset_tag')}) - Status corrected"
                            
                            return {
                                'message': corrected_message,
                                'asset_info': final_asset_info
                            }
                    else:
                        logger.error(f"Failed to force update asset {asset_id}: {fix_response}")
            
            # Create enhanced message even for delayed checkout
            asset_name = "Asset"
            inventory_display = ""
            
            if updated_asset_info:
                asset_name = updated_asset_info.get('name')
                if not asset_name:
                    # Use model name for unnamed assets (like microphones)
                    model_name = updated_asset_info.get('model', {}).get('name')
                    if model_name:
                        asset_name = model_name
                    else:
                        asset_name = f"Asset {updated_asset_info.get('asset_tag')}"
                
                inventory_number = get_inventory_display_number(updated_asset_info)
                if inventory_number and inventory_number != updated_asset_info.get('asset_tag'):
                    inventory_display = f" (Inventory: {inventory_number})"
                else:
                    inventory_display = f" (Tag: {updated_asset_info.get('asset_tag')})"
            
            delayed_message = f"{asset_name}{inventory_display} checkout processed, but assignment may be delayed. Please check your dashboard in a moment."
            
            return {
                'message': delayed_message,
                'asset_info': updated_asset_info
            }
    else:
        log_security_event("ASSET_CHECKOUT_FAILED", f"Failed to checkout asset {asset_id}: {data}", user_id)
        logger.error(f"Asset checkout failed: {data}")
        return {'error': f"Failed to check out asset: {data}"}

def transfer_asset(barcode_data, from_user_id, to_user_id):
    """Handles asset transfer from one user to another."""
    if not barcode_data or not from_user_id or not to_user_id:
        return {'error': "Missing required parameters for transfer."}
    
    try:
        asset_id = extract_asset_id_from_barcode(barcode_data)
    except ValueError as e:
        return {'error': str(e)}
    
    # Get asset info to verify current assignment
    asset_info = get_asset_info(asset_id)
    if not asset_info:
        return {'error': "Asset not found."}
    
    # Verify the asset is currently assigned to the from_user
    if not is_asset_assigned_to_user(asset_info, from_user_id):
        return {'error': "Asset is not currently assigned to the specified user."}
    
    # Perform the transfer by checking out to new user
    payload = {
        "status_id": 2,  # Ready to Deploy status
        "checkout_to_type": "user",
        "assigned_user": int(to_user_id),
        "note": "Transferred via kiosk"
    }
    
    logger.debug(f"Attempting transfer with payload: {payload}")
    
    success, data = make_api_request(
        'POST', 
        f"/hardware/{asset_info['id']}/checkout",
        json=payload
    )
    
    if success:
        log_security_event("ASSET_TRANSFER", f"Asset {asset_id} transferred from user {from_user_id} to user {to_user_id}", to_user_id)
        logger.info(f"Asset {asset_id} transfer API call succeeded")
        
        # Wait a moment and verify the transfer
        import time
        time.sleep(2.0)
        
        updated_asset_info = get_asset_info(asset_id)
        
        if updated_asset_info and is_asset_assigned_to_user(updated_asset_info, to_user_id):
            logger.info(f"Asset {asset_id} successfully transferred to user {to_user_id}")
            
            # Create enhanced transfer message with asset name and inventory number
            asset_name = updated_asset_info.get('name')
            if not asset_name:
                # Use model name for unnamed assets (like microphones)
                model_name = updated_asset_info.get('model', {}).get('name')
                if model_name:
                    asset_name = model_name
                else:
                    asset_name = f"Asset {updated_asset_info.get('asset_tag')}"
            
            inventory_number = get_inventory_display_number(updated_asset_info)
            
            if inventory_number and inventory_number != updated_asset_info.get('asset_tag'):
                transfer_message = f"Successfully transferred: {asset_name} (Inventory: {inventory_number}) to you"
            else:
                transfer_message = f"Successfully transferred: {asset_name} (Tag: {updated_asset_info.get('asset_tag')}) to you"
            
            return {
                'message': transfer_message,
                'asset_info': updated_asset_info
            }
        else:
            return {'error': f"Transfer failed - asset assignment did not update properly."}
    else:
        log_security_event("ASSET_TRANSFER_FAILED", f"Failed to transfer asset {asset_id}: {data}", to_user_id)
        logger.error(f"Asset transfer failed: {data}")
        return {'error': f"Failed to transfer asset: {data}"}

def checkin_asset(barcode_data, user_id):
    """Handles asset check-in."""
    if not barcode_data or not user_id:
        return {'error': "Missing required parameters."}
    
    try:
        asset_id = extract_asset_id_from_barcode(barcode_data)
    except ValueError as e:
        return {'error': str(e)}
    
    # Check if asset exists
    asset_info = get_asset_info(asset_id)
    if not asset_info:
        return {'error': "Asset not found."}

    # Check if asset is currently checked out
    if not is_asset_checked_out(asset_info):
        return {'error': "Asset is not currently checked out."}

    # Check who the asset is assigned to
    is_assigned_to_user = is_asset_assigned_to_user(asset_info, user_id)
    
    assigned_name = "Unknown User"
    if not is_assigned_to_user:
        # Asset is assigned to someone else - allow but log it specially
        assigned_user = asset_info.get('assigned_to', {})
        if assigned_user:
            assigned_name = assigned_user.get('name', 'Unknown User')
            assigned_id = assigned_user.get('id', 'Unknown')
        else:
            assigned_name = "No one"
            assigned_id = "None"
        
        log_security_event(
            "CROSS_USER_CHECKIN", 
            f"User {user_id} returning asset {asset_id} assigned to user {assigned_id} ({assigned_name})", 
            user_id
        )
        logger.info(f"Cross-user checkin: User {user_id} returning asset {asset_id} assigned to {assigned_name}")

    payload = {
        "note": f"Checked in via kiosk by user {user_id}" + (
            f" (originally assigned to {assigned_name})" if not is_assigned_to_user else ""
        )
    }

    success, data = make_api_request(
        'POST',
        f"/hardware/{asset_info['id']}/checkin",
        json=payload
    )
    
    if success:
        event_type = "ASSET_CHECKIN" if is_assigned_to_user else "CROSS_USER_ASSET_CHECKIN"
        log_security_event(event_type, f"Asset {asset_id} checked in", user_id)
        
        # Update status to "Ready to Deploy" after successful checkin
        # This ensures the asset shows as available for future checkouts
        import time
        time.sleep(1)  # Give the checkin API time to complete
        
        status_update_payload = {
            "status_id": 2  # "Ready to Deploy"
        }
        
        status_success, status_response = make_api_request(
            'PATCH', 
            f'/hardware/{asset_info["id"]}', 
            json=status_update_payload
        )
        
        if status_success:
            logger.info(f"Asset {asset_id} status updated to 'Ready to Deploy' after checkin")
        else:
            logger.warning(f"Failed to update status for asset {asset_id} after checkin: {status_response}")
        
        if is_assigned_to_user:
            return {'message': "Asset checked in successfully."}
        else:
            return {
                'message': f"Asset returned successfully. (Note: This was assigned to {assigned_name})",
                'warning': f"Asset was originally assigned to {assigned_name}"
            }
    else:
        log_security_event("ASSET_CHECKIN_FAILED", f"Failed to checkin asset {asset_id}: {data}", user_id)
        return {'error': f"Failed to check in asset: {data}"}

def get_user_assigned_assets(user_id):
    """Fetch all assets assigned to a user from Snipe-IT efficiently."""
    if not user_id:
        logger.warning("get_user_assigned_assets called with empty user_id")
        return []
    
    logger.debug(f"Fetching assets for user_id: {user_id}")
    
    
    # First, try to get user's assigned assets directly using the users endpoint
    # This is often more efficient than filtering all hardware
    try:
        success, user_data = make_api_request('GET', f'/users/{user_id}')
        if success and user_data:
            if 'assets' in user_data:
                # Some Snipe-IT versions include assets in the user object
                assets = user_data.get('assets', [])
                if assets:
                    logger.info(f"Found {len(assets)} assets from user endpoint")
                    return sanitize_json_response(assets)
    except Exception as e:
        logger.debug(f"User endpoint approach failed: {e}")
    
    # If that doesn't work, try the hardware endpoint with user filter
    # The key insight: Snipe-IT requires 'expand' parameter to include assignment data
    # Also need to include all status types since assigned assets might have various statuses
    filter_params = [
        # Include all statuses - some assigned assets may be in "Ready to Deploy" status
        {'expand': 'assigned_to,status_label', 'limit': 2000, 'status': 'all'},
        # Try with specific user assignment
        {'assigned_to': int(user_id), 'expand': 'assigned_to,status_label', 'status': 'all'},
        # Alternative user parameter
        {'assigned_user': int(user_id), 'expand': 'assigned_to,status_label', 'status': 'all'},
        # Original method without status filter
        {'expand': 'assigned_to,status_label', 'limit': 2000}
    ]
    
    all_verified_assets = []
    asset_tags_seen = set()  # Track assets to avoid duplicates
    
    for params in filter_params:
        try:
            success, data = make_api_request('GET', '/hardware', params=params)
            if success:
                assets = data.get('rows', [])
                
                # Debug logging with detailed info
                logger.info(f"DEBUG: API query {params} returned {len(assets)} total assets")
                
                # Log first few assets to see what's being returned
                for i, asset in enumerate(assets[:3]):  # Show first 3 assets
                    assigned_to = asset.get('assigned_to')
                    assigned_id = assigned_to.get('id') if assigned_to else None
                    logger.info(f"DEBUG: Asset {i+1}: Tag={asset.get('asset_tag')}, Name={asset.get('name')}, AssignedTo={assigned_id}, Status={asset.get('status_label', {}).get('name')}")
                
                # Verify the assets are actually assigned to our user
                param_verified_assets = []
                for asset in assets:
                    assigned_to = asset.get('assigned_to')
                    if assigned_to and assigned_to.get('id') == int(user_id):
                        asset_tag = asset.get('asset_tag')
                        # Only add if we haven't seen this asset before
                        if asset_tag and asset_tag not in asset_tags_seen:
                            all_verified_assets.append(asset)
                            asset_tags_seen.add(asset_tag)
                            param_verified_assets.append(asset)
                            logger.info(f"DEBUG: Found asset {asset.get('name')} (Tag: {asset_tag}) assigned to user {user_id}")
                
                logger.info(f"DEBUG: Parameter {params} found {len(param_verified_assets)} new user assets")
                    
        except Exception as e:
            logger.info(f"DEBUG: Parameter {params} failed: {e}")
            continue
    
    # Try name search first since API filtering is unreliable
    try:
        # Get user info to find their name
        success, user_data = make_api_request('GET', f'/users/{user_id}')
        if success and user_data and user_data.get('name'):
            user_name = user_data['name']
            # Search for assets checked out to this user by name
            success, search_data = make_api_request('GET', '/hardware', params={
                'search': user_name,
                'expand': 'assigned_to,status_label,model',
                'limit': 100
            })
            
            if success:
                search_assets = search_data.get('rows', [])
                logger.info(f"DEBUG: Name search for '{user_name}' returned {len(search_assets)} assets")
                
                # Filter to assets actually assigned to this user
                name_verified_assets = []
                for asset in search_assets:
                    assigned_to = asset.get('assigned_to')
                    if assigned_to and assigned_to.get('id') == int(user_id):
                        asset_tag = asset.get('asset_tag')
                        if asset_tag and asset_tag not in asset_tags_seen:
                            all_verified_assets.append(asset)
                            asset_tags_seen.add(asset_tag)
                            name_verified_assets.append(asset)
                            logger.info(f"DEBUG: Name search found asset {asset.get('name')} (Tag: {asset_tag}) assigned to user {user_id}")
                
                logger.info(f"DEBUG: Name search found {len(name_verified_assets)} additional user assets")
    except Exception as e:
        logger.info(f"DEBUG: Name search failed: {e}")
                
    # Additional search: Look through more assets to find ones with empty names
    # This catches microphones and other assets that don't show up in name search
    if len(all_verified_assets) < 10:  # Only do this if we haven't found many assets yet
        try:
            success, broad_search = make_api_request('GET', '/hardware', params={
                'expand': 'assigned_to,status_label,model',
                'limit': 1000,  # Search through more assets
                'status': 'all'
            })
            
            if success:
                broad_assets = broad_search.get('rows', [])
                logger.info(f"DEBUG: Broad search returned {len(broad_assets)} assets")
                
                # Look for assets assigned to this user that we missed
                broad_verified_assets = []
                for asset in broad_assets:
                    assigned_to = asset.get('assigned_to')
                    if assigned_to and assigned_to.get('id') == int(user_id):
                        asset_tag = asset.get('asset_tag')
                        if asset_tag and asset_tag not in asset_tags_seen:
                            all_verified_assets.append(asset)
                            asset_tags_seen.add(asset_tag)
                            broad_verified_assets.append(asset)
                            asset_name = asset.get('name') or f"Asset {asset_tag}"
                            logger.info(f"DEBUG: Broad search found asset {asset_name} (Tag: {asset_tag}) assigned to user {user_id}")
                
                logger.info(f"DEBUG: Broad search found {len(broad_verified_assets)} additional user assets")
        except Exception as e:
            logger.info(f"DEBUG: Broad search failed: {e}")
    
    if all_verified_assets:
        logger.info(f"DEBUG: Total verified assets from all methods: {len(all_verified_assets)}")
        return sanitize_json_response(all_verified_assets)
    
    # Final fallback: Try to find recently checked out assets by searching for the user's name
    # This helps catch assets that might not show up in hardware API due to status issues
    try:
        # Get user info to find their name
        success, user_data = make_api_request('GET', f'/users/{user_id}')
        if success and user_data and user_data.get('name'):
            user_name = user_data['name']
            # Search for assets checked out to this user by name
            success, search_data = make_api_request('GET', '/hardware', params={
                'search': user_name, 
                'expand': 'assigned_to,status_label',
                'limit': 50
            })
            if success:
                search_assets = search_data.get('rows', [])
                user_assets = []
                for asset in search_assets:
                    assigned_to = asset.get('assigned_to', {})
                    if assigned_to and assigned_to.get('id') == int(user_id):
                        user_assets.append(asset)
                        logger.debug(f"Found user asset via search: {asset.get('name')} (Status: {asset.get('status_label', {}).get('name', 'Unknown')})")
                
                if user_assets:
                    logger.info(f"Found {len(user_assets)} assets for user {user_id} via name search")
                    return sanitize_json_response(user_assets)
    except Exception as e:
        logger.debug(f"Name search fallback failed: {e}")

    # Minimal fallback - check only first 2 pages for performance
    logger.debug("Final fallback: checking first 100 assets only")
    assigned_assets = []
    
    for page in range(1, 3):  # Only check first 100 assets
        try:
            params = {'limit': 50, 'offset': (page - 1) * 50, 'expand': 'assigned_to,status_label'}
            success, data = make_api_request('GET', '/hardware', params=params)
            
            if not success:
                break
                
            assets_page = data.get('rows', [])
            if not assets_page:
                break
                
            # Find assets assigned to this user
            for asset in assets_page:
                assigned_to = asset.get('assigned_to')
                if assigned_to and assigned_to.get('id') == int(user_id):
                    assigned_assets.append(asset)
                    logger.debug(f"Found user asset via pagination: {asset.get('name')} (Status: {asset.get('status_label', {}).get('name', 'Unknown')})")
                    
        except Exception as e:
            logger.debug(f"Page {page} failed: {e}")
            break
    
    logger.info(f"Found {len(assigned_assets)} assets for user {user_id}")
    return sanitize_json_response(assigned_assets)

def check_user_vip_status(employee_num):
    """Check if a user is VIP by their employee number."""
    if not employee_num or not str(employee_num).strip():
        return False, "Missing employee number"
    
    success, data = make_api_request('GET', '/users', params={'employee_num': str(employee_num).strip(), 'limit': 1})
    
    if not success:
        logger.error(f"Failed to check VIP status: {data}")
        return False, f"API error: {data}"
    
    if 'rows' in data and len(data['rows']) > 0:
        user_data = data['rows'][0]
        is_vip = user_data.get('vip', 0) == 1
        user_name = user_data.get('name', 'Unknown')
        logger.debug(f"User {user_name} (Employee: {employee_num}) VIP status: {is_vip}")
        return is_vip, user_data
    else:
        logger.warning(f"No user found for employee number: {employee_num}")
        return False, "User not found"

def create_user(user_data):
    """
    Create a new user in Snipe-IT.
    
    Args:
        user_data (dict): User information with required fields:
            - first_name, last_name, username, email (required)
            - employee_num, password, vip (optional)
            
    Returns:
        tuple: (success: bool, data_or_error: dict/str)
    """
    if not user_data:
        return False, "Missing user data"
    
    required_fields = ['first_name', 'last_name', 'username', 'email']
    for field in required_fields:
        if not user_data.get(field):
            return False, f"Missing required field: {field}"
    
    payload = {
        "first_name": user_data['first_name'].strip(),
        "last_name": user_data['last_name'].strip(),
        "username": user_data['username'].strip(),
        "email": user_data['email'].strip().lower(),
        "activated": True,
    }
    
    if user_data.get('employee_num'):
        payload['employee_num'] = str(user_data['employee_num']).strip()
    
    if user_data.get('password'):
        payload['password'] = user_data['password']
        payload['password_confirmation'] = user_data['password']
    
    if user_data.get('vip'):
        payload['vip'] = 1 if user_data['vip'] else 0
    
    if user_data.get('department_id'):
        payload['department_id'] = user_data['department_id']
    
    logger.debug(f"Creating user: {payload['username']}")
    
    success, response = make_api_request('POST', 'users', json=payload)
    
    if success:
        logger.info(f"User created: {payload['username']}")
        log_security_event("USER_CREATED", f"Created user {payload['username']}")
        return True, response
    else:
        logger.error(f"User creation failed: {response}")
        return False, response

def lookup_assets_by_user_name(search_name):
    """
    Look up all assets assigned to a user by their name (with fuzzy matching).
    Returns both current and historical assignments.
    """
    logger.debug(f"Looking up assets for user name: {search_name}")
    
    # Search for users by name with fuzzy matching
    user_success, user_data = make_api_request('GET', '/users', params={
        'search': str(search_name).strip(),
        'limit': 50  # Get more results for fuzzy matching
    })
    
    if not user_success:
        logger.error(f"Failed to search for user: {user_data}")
        return False, f"API error: {user_data}"
    
    if 'rows' not in user_data or len(user_data['rows']) == 0:
        logger.warning(f"No users found matching name: {search_name}")
        return False, "No users found matching that name"
    
    # Find best match using fuzzy string matching
    search_term = search_name.lower().strip()
    matched_users = []
    
    for user in user_data['rows']:
        user_name = user.get('name', '').lower()
        if not user_name:
            continue
            
        # Exact match gets highest priority
        if search_term == user_name:
            matched_users.insert(0, {'user': user, 'score': 100})
            continue
            
        # Check if search term is contained in name
        if search_term in user_name:
            score = 90 - abs(len(user_name) - len(search_term)) * 2  # Prefer closer length matches
            matched_users.append({'user': user, 'score': score})
            continue
            
        # Check if name contains search term words
        search_words = search_term.split()
        name_words = user_name.split()
        matching_words = sum(1 for word in search_words if any(word in name_word for name_word in name_words))
        
        if matching_words > 0:
            score = (matching_words / len(search_words)) * 80
            matched_users.append({'user': user, 'score': score})
            continue
            
        # Basic fuzzy matching - check for similar character sequences
        common_chars = sum(1 for char in search_term if char in user_name)
        if common_chars >= len(search_term) * 0.6:  # 60% character overlap
            score = (common_chars / max(len(search_term), len(user_name))) * 60
            matched_users.append({'user': user, 'score': score})
    
    if not matched_users:
        logger.warning(f"No users found with fuzzy matching for: {search_name}")
        return False, f"No users found matching '{search_name}'"
    
    # Sort by match score and take the best match
    matched_users.sort(key=lambda x: x['score'], reverse=True)
    best_match = matched_users[0]['user']
    user_id = best_match['id']
    user_name = best_match.get('name', 'Unknown')
    
    logger.info(f"Best match for '{search_name}': {user_name} (Score: {matched_users[0]['score']:.1f})")
    
    # Get assets assigned to this user
    assets_success, assets_data = make_api_request('GET', f'/users/{user_id}/assets')
    
    if not assets_success:
        logger.error(f"Failed to get assets for user {user_name}: {assets_data}")
        return False, f"API error: {assets_data}"
    
    # Process assets to include inventory display numbers
    assets = assets_data.get('rows', [])
    for asset in assets:
        asset['inventory_display_number'] = get_inventory_display_number(asset)
    
    logger.info(f"Found {len(assets)} assets for user {user_name}")
    
    # Include multiple matches if there are other good candidates
    other_matches = [match['user'] for match in matched_users[1:4] if match['score'] >= 70]  # Top 3 alternatives with good scores
    
    return True, {
        'user': best_match,
        'assets': assets,
        'total_assets': len(assets),
        'match_score': matched_users[0]['score'],
        'other_matches': other_matches
    }

def lookup_asset_by_number(asset_identifier):
    """
    Look up an asset by asset tag or inventory number.
    Returns asset info including current assignment.
    """
    logger.debug(f"Looking up asset: {asset_identifier}")
    
    # First try by asset tag
    asset_success, asset_data = make_api_request('GET', f'/hardware/bytag/{asset_identifier}')
    
    if asset_success and asset_data:
        # Asset found by tag
        asset_data['inventory_display_number'] = get_inventory_display_number(asset_data)
        return True, asset_data
    
    # If not found by tag, search by custom fields (inventory numbers)
    search_success, search_data = make_api_request('GET', '/hardware', params={
        'search': asset_identifier,
        'limit': 50
    })
    
    if not search_success:
        logger.error(f"Failed to search for asset {asset_identifier}: {search_data}")
        return False, f"API error: {search_data}"
    
    # Look through search results for matching inventory numbers
    assets = search_data.get('rows', [])
    for asset in assets:
        inventory_num = get_inventory_display_number(asset)
        if inventory_num == asset_identifier:
            logger.info(f"Found asset by inventory number: {asset_identifier}")
            asset['inventory_display_number'] = inventory_num
            return True, asset
    
    logger.warning(f"Asset not found: {asset_identifier}")
    return False, "Asset not found"

def get_user_info_by_id(user_id):
    """Get user information by user ID from Snipe-IT."""
    logger.debug(f"Getting user info for ID: {user_id}")
    
    success, data = make_api_request('GET', f'/users/{user_id}')
    
    if not success:
        logger.error(f"Failed to get user info for ID {user_id}: {data}")
        return None
    
    if data:
        logger.debug(f"Retrieved user info for ID {user_id}: {data.get('name')}")
        return data
    else:
        logger.warning(f"No user found with ID: {user_id}")
        return None

def get_departments():
    """Get list of all departments from Snipe-IT."""
    logger.debug("Fetching departments from Snipe-IT")
    
    success, data = make_api_request('GET', '/departments', params={'limit': 500})
    
    if not success:
        logger.error(f"Failed to get departments: {data}")
        return []
    
    departments = []
    if 'rows' in data:
        for dept in data['rows']:
            departments.append({
                'id': dept['id'],
                'name': dept['name'],
                'notes': dept.get('notes', ''),
                'manager': dept.get('manager', {}).get('name') if dept.get('manager') else None
            })
        
        logger.info(f"Retrieved {len(departments)} departments")
    
    return departments
