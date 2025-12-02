"""
Asset Service - Business logic for asset operations
Handles checkout, checkin, transfer, and asset information retrieval
"""
import logging
from typing import Tuple, Dict, Any, Optional
from utils.snipe_it_api import (
    checkout_asset as api_checkout_asset,
    checkin_asset as api_checkin_asset,
    transfer_asset as api_transfer_asset,
    get_asset_info as api_get_asset_info,
    is_asset_assigned_to_user,
    get_user_assigned_assets,
    is_asset_checked_out,
    lookup_asset_by_number
)
from utils.security import log_security_event

logger = logging.getLogger(__name__)


class AssetService:
    """Service class for asset management operations"""

    @staticmethod
    def checkout_asset(asset_id: str, user_id: int, notes: str = "") -> Tuple[bool, Any]:
        """
        Checkout an asset to a user

        Args:
            asset_id: Asset ID to checkout (can be asset tag or ID)
            user_id: User ID to checkout to
            notes: Optional checkout notes (currently unused by API)

        Returns:
            Tuple of (success, result)
        """
        logger.info(f"Checking out asset {asset_id} to user {user_id}")
        log_security_event("ASSET_CHECKOUT_ATTEMPT", f"Asset {asset_id} to user {user_id}", user_id)

        # The API function expects (barcode_data, user_id) and returns a dict
        result = api_checkout_asset(asset_id, user_id)

        # Check if result contains an error
        if result and 'error' not in result:
            log_security_event("ASSET_CHECKOUT_SUCCESS", f"Asset {asset_id} checked out to user {user_id}", user_id)
            logger.info(f"Successfully checked out asset {asset_id} to user {user_id}")
            return True, result
        else:
            error_msg = result.get('error', 'Unknown error') if result else 'Checkout failed'
            log_security_event("ASSET_CHECKOUT_FAILURE", f"Failed to checkout asset {asset_id}: {error_msg}", user_id)
            logger.error(f"Failed to checkout asset {asset_id}: {error_msg}")
            return False, error_msg

    @staticmethod
    def checkin_asset(asset_id: str, user_id: int, notes: str = "") -> Tuple[bool, Any]:
        """
        Check in an asset

        Args:
            asset_id: Asset ID to checkin (can be asset tag or ID)
            user_id: User ID performing checkin
            notes: Optional checkin notes (currently unused by API)

        Returns:
            Tuple of (success, result)
        """
        logger.info(f"Checking in asset {asset_id}")
        log_security_event("ASSET_CHECKIN_ATTEMPT", f"Asset {asset_id}", user_id)

        # The API function expects (barcode_data, user_id) and returns a dict
        result = api_checkin_asset(asset_id, user_id)

        # Check if result contains an error
        if result and 'error' not in result:
            log_security_event("ASSET_CHECKIN_SUCCESS", f"Asset {asset_id} checked in", user_id)
            logger.info(f"Successfully checked in asset {asset_id}")
            return True, result
        else:
            error_msg = result.get('error', 'Unknown error') if result else 'Checkin failed'
            log_security_event("ASSET_CHECKIN_FAILURE", f"Failed to checkin asset {asset_id}: {error_msg}", user_id)
            logger.error(f"Failed to checkin asset {asset_id}: {error_msg}")
            return False, error_msg

    @staticmethod
    def transfer_asset(asset_id: str, target_user_id: int, current_user_id: int, notes: str = "") -> Tuple[bool, Any]:
        """
        Transfer an asset from one user to another

        Args:
            asset_id: Asset ID to transfer (can be asset tag or ID)
            target_user_id: Target user ID
            current_user_id: Current user ID performing transfer
            notes: Optional transfer notes (currently unused by API)

        Returns:
            Tuple of (success, result)
        """
        logger.info(f"Transferring asset {asset_id} to user {target_user_id}")
        log_security_event("ASSET_TRANSFER_ATTEMPT", f"Asset {asset_id} to user {target_user_id}", current_user_id)

        # Get asset info to find current owner
        asset_info = api_get_asset_info(asset_id)
        if not asset_info:
            error_msg = "Asset not found"
            log_security_event("ASSET_TRANSFER_FAILURE", f"Failed to transfer asset {asset_id}: {error_msg}", current_user_id)
            return False, error_msg

        # Get current owner ID
        from_user_id = None
        if asset_info.get('assigned_to'):
            from_user_id = asset_info['assigned_to'].get('id')

        if not from_user_id:
            error_msg = "Asset is not currently assigned to anyone"
            log_security_event("ASSET_TRANSFER_FAILURE", f"Failed to transfer asset {asset_id}: {error_msg}", current_user_id)
            return False, error_msg

        # The API function expects (barcode_data, from_user_id, to_user_id) and returns a dict
        result = api_transfer_asset(asset_id, from_user_id, target_user_id)

        # Check if result contains an error
        if result and 'error' not in result:
            log_security_event("ASSET_TRANSFER_SUCCESS", f"Asset {asset_id} transferred to user {target_user_id}", current_user_id)
            logger.info(f"Successfully transferred asset {asset_id} to user {target_user_id}")
            return True, result
        else:
            error_msg = result.get('error', 'Unknown error') if result else 'Transfer failed'
            log_security_event("ASSET_TRANSFER_FAILURE", f"Failed to transfer asset {asset_id}: {error_msg}", current_user_id)
            logger.error(f"Failed to transfer asset {asset_id}: {error_msg}")
            return False, error_msg

    @staticmethod
    def get_asset_info(identifier: str, user_id: Optional[int] = None) -> Tuple[bool, Any]:
        """
        Get asset information by barcode or asset tag

        Args:
            identifier: Barcode or asset tag
            user_id: Optional user ID for logging

        Returns:
            Tuple of (success, asset_data)
        """
        logger.info(f"Looking up asset info for: {identifier}")

        result = api_get_asset_info(identifier)

        if result:
            logger.info(f"Asset info retrieved successfully for {identifier}")
            return True, result
        else:
            error_msg = "Asset not found or invalid barcode"
            logger.warning(f"Failed to retrieve asset info for {identifier}")
            if user_id:
                log_security_event("ASSET_LOOKUP_FAILURE", f"Failed to lookup {identifier}", user_id)
            return False, error_msg

    @staticmethod
    def is_asset_assigned_to_user(asset_id: int, user_id: int) -> bool:
        """
        Check if an asset is assigned to a specific user

        Args:
            asset_id: Asset ID to check
            user_id: User ID to check against

        Returns:
            True if asset is assigned to user, False otherwise
        """
        return is_asset_assigned_to_user(asset_id, user_id)

    @staticmethod
    def get_user_assigned_assets(user_id: int) -> list:
        """
        Get all assets assigned to a user

        Args:
            user_id: User ID

        Returns:
            List of assets assigned to the user
        """
        logger.info(f"Retrieving assigned assets for user {user_id}")
        return get_user_assigned_assets(user_id)

    @staticmethod
    def is_asset_checked_out(asset_id: int) -> Tuple[bool, Optional[int]]:
        """
        Check if an asset is currently checked out

        Args:
            asset_id: Asset ID to check

        Returns:
            Tuple of (is_checked_out, assigned_user_id)
        """
        return is_asset_checked_out(asset_id)

    @staticmethod
    def lookup_asset_by_number(asset_number: str) -> Tuple[bool, Any]:
        """
        Look up an asset by its asset number

        Args:
            asset_number: Asset number/tag to lookup

        Returns:
            Tuple of (success, asset_data)
        """
        logger.info(f"Looking up asset by number: {asset_number}")
        return lookup_asset_by_number(asset_number)


# Singleton instance
asset_service = AssetService()
