"""
Loan Agreement Service - Business logic for loan agreements
Handles signature processing, agreement submission, and equipment checkout
"""
import logging
import os
import time
from typing import Tuple, Dict, Any, List, Optional
from utils.security import (
    validate_filename,
    validate_base64_image,
    validate_user_input,
    log_security_event
)
from utils.snipe_it_api import checkout_asset, get_user_info_by_id

logger = logging.getLogger(__name__)


class LoanAgreementService:
    """Service class for loan agreement operations"""

    def __init__(self, signatures_dir='/var/www/kiosk/loan_agreements/signatures'):
        self.signatures_dir = signatures_dir
        os.makedirs(self.signatures_dir, exist_ok=True)

    def validate_vip_user(self, user_id: int) -> Tuple[bool, Optional[Dict], str]:
        """
        Validate that user is VIP and can submit loan agreements

        Args:
            user_id: User ID to validate

        Returns:
            Tuple of (is_valid, user_info, error_message)
        """
        if not user_id:
            return False, None, "Authentication required"

        user_info = get_user_info_by_id(user_id)
        if not user_info:
            return False, None, "User not found"

        if not user_info.get('vip'):
            log_security_event("LOAN_AGREEMENT_ACCESS_DENIED",
                             f"Non-VIP user {user_id} attempted loan agreement submission", user_id)
            return False, None, "VIP access required"

        return True, user_info, ""

    def process_signature(self, signature_data: str, agreement_id: str,
                         borrower_name: str, sig_type: str = "student") -> Tuple[bool, str, str]:
        """
        Process and save a signature image

        Args:
            signature_data: Base64 encoded signature image
            agreement_id: Agreement ID
            borrower_name: Name of borrower for filename
            sig_type: Type of signature (student, coordinator, etc)

        Returns:
            Tuple of (success, filename, error_message)
        """
        try:
            # Validate borrower name for filename
            is_valid, safe_name, error = validate_user_input(borrower_name, 50, "borrower_name")
            if not is_valid:
                return False, "", f"Invalid borrower name: {error}"

            # Sanitize name for filename
            safe_name = safe_name.replace(" ", "_").replace(".", "").replace("/", "").replace("\\", "")
            filename = f'{agreement_id}_{sig_type}_{safe_name}.png'

            # Validate filename security
            is_valid, secure_filename, error = validate_filename(filename)
            if not is_valid:
                return False, "", f"Invalid filename: {error}"

            # Validate and decode image data
            is_valid, decoded_image, error = validate_base64_image(signature_data)
            if not is_valid:
                log_security_event("FILE_UPLOAD_THREAT", f"Invalid signature upload: {error}")
                return False, "", f"Invalid signature image: {error}"

            # Construct filepath
            filepath = os.path.join(self.signatures_dir, secure_filename)

            # Prevent path traversal
            if not os.path.abspath(filepath).startswith(os.path.abspath(self.signatures_dir)):
                log_security_event("SECURITY_THREAT", "Path traversal attempt in signature upload")
                return False, "", "Security violation detected"

            # Save signature
            with open(filepath, 'wb') as f:
                f.write(decoded_image)

            logger.info(f"{sig_type.capitalize()} signature saved: {filename}")
            return True, filename, ""

        except Exception as e:
            logger.error(f"Error processing signature: {e}")
            return False, "", str(e)

    def save_agreement_summary(self, agreement_id: str, data: Dict[str, Any],
                              coordinator_name: str, student_filename: str,
                              equipment_list: List[Dict]) -> Tuple[bool, str]:
        """
        Save loan agreement summary to text file

        Args:
            agreement_id: Agreement ID
            data: Form data
            coordinator_name: Name of coordinator confirming
            student_filename: Student signature filename
            equipment_list: List of equipment being loaned

        Returns:
            Tuple of (success, filename)
        """
        try:
            summary_filename = f'{agreement_id}_summary.txt'
            summary_filepath = os.path.join(self.signatures_dir, summary_filename)

            with open(summary_filepath, 'w') as f:
                f.write("LOAN AGREEMENT SUMMARY\n")
                f.write(f"Agreement ID: {agreement_id}\n")
                f.write(f"Date Submitted: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Confirmed By (Coordinator): {coordinator_name}\n\n")

                f.write("BORROWER INFORMATION:\n")
                f.write(f"Name: {data.get('borrower_name', 'N/A')}\n")
                f.write(f"Email: {data.get('rit_email', 'N/A')}\n")
                f.write(f"Location: {data.get('campus_location', 'N/A')}\n\n")

                f.write("DATES OF USE:\n")
                f.write(f"Start Date: {data.get('start_date', 'N/A')}\n")
                f.write(f"End Date: {data.get('end_date', 'N/A')}\n\n")

                f.write("EQUIPMENT:\n")
                if equipment_list:
                    for i, equipment in enumerate(equipment_list, 1):
                        f.write(f"{i}. {equipment.get('name', 'Unknown')}\n")
                        f.write(f"   Asset Tag: {equipment.get('asset_tag', 'N/A')}\n")
                        f.write(f"   Inventory Number: {equipment.get('inventory_number', 'N/A')}\n")
                        f.write(f"   Type: {equipment.get('equipment_type', 'Unknown')}\n")
                        if equipment.get('assigned_to'):
                            f.write(f"   Previously Assigned To: {equipment.get('assigned_to')}\n")
                        f.write("\n")
                else:
                    # Fallback for old format
                    f.write(f"iPad Number: {data.get('ipad_number', 'N/A')}\n")
                    f.write(f"Microphone Number: {data.get('microphone_number', 'N/A')}\n\n")

                f.write("CONFIRMATION:\n")
                f.write(f"Student Signature File: {student_filename}\n")
                f.write(f"Confirmed By: {coordinator_name} (Logged in user)\n")
                f.write(f"Signature Date: {data.get('signature_date', 'N/A')}\n")

            return True, summary_filename

        except Exception as e:
            logger.error(f"Error saving agreement summary: {e}")
            return False, ""

    def checkout_equipment(self, student_id: int, equipment_list: List[Dict]) -> Dict[str, Any]:
        """
        Checkout all equipment in the list to the student

        Args:
            student_id: Student ID to checkout to
            equipment_list: List of equipment to checkout

        Returns:
            Dict with checkout results
        """
        checkout_results = []
        checkout_errors = []

        if not student_id or not equipment_list:
            logger.warning("No student_id or equipment_list provided for checkout")
            return {
                'successful': [],
                'failed': [],
                'total_items': 0,
                'successful_count': 0,
                'failed_count': 0
            }

        logger.info(f"Attempting to check out {len(equipment_list)} items to student {student_id}")

        for equipment in equipment_list:
            asset_tag = equipment.get('asset_tag')
            equipment_name = equipment.get('name', 'Unknown')

            if not asset_tag:
                error_msg = f"{equipment_name}: No asset tag provided"
                checkout_errors.append(error_msg)
                continue

            try:
                result = checkout_asset(asset_tag, student_id)
                if result.get('error'):
                    error_msg = f"{equipment_name} ({asset_tag}): {result['error']}"
                    checkout_errors.append(error_msg)
                    logger.error(f"Failed to check out {asset_tag}: {result['error']}")
                else:
                    success_msg = f"{equipment_name} ({asset_tag}): Successfully checked out"
                    checkout_results.append(success_msg)
                    logger.info(f"Successfully checked out {asset_tag} to student {student_id}")
            except Exception as checkout_error:
                error_msg = f"{equipment_name} ({asset_tag}): Checkout error - {str(checkout_error)}"
                checkout_errors.append(error_msg)
                logger.error(f"Exception during checkout of {asset_tag}: {checkout_error}")

        return {
            'successful': checkout_results,
            'failed': checkout_errors,
            'total_items': len(equipment_list),
            'successful_count': len(checkout_results),
            'failed_count': len(checkout_errors)
        }

    def submit_loan_agreement(self, user_id: int, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Process complete loan agreement submission

        Args:
            user_id: User ID submitting the agreement
            data: Form data including signatures and equipment

        Returns:
            Tuple of (success, response_data)
        """
        # Validate VIP user
        is_valid, user_info, error = self.validate_vip_user(user_id)
        if not is_valid:
            return False, {'error': error}

        # Generate agreement ID
        agreement_id = f'LA-{user_id}-{int(time.time())}'
        borrower_name = data.get('borrower_name', 'Unknown')
        coordinator_name = user_info.get('name', 'Unknown Coordinator')
        equipment_list = data.get('equipment_list', [])

        # Generate equipment summary for logging
        if equipment_list:
            equipment_summary = ', '.join([
                f"{eq.get('name', 'Unknown')} ({eq.get('asset_tag', 'No tag')})"
                for eq in equipment_list
            ])
        else:
            equipment_summary = f"iPad: {data.get('ipad_number', 'N/A')}, Microphone: {data.get('microphone_number', 'N/A')}"

        # Process student signature
        student_signature = data.get('student_signature')
        if not student_signature:
            return False, {'error': 'Student signature is required'}

        success, student_filename, error = self.process_signature(
            student_signature, agreement_id, borrower_name, "student"
        )
        if not success:
            return False, {'error': error}

        # Save agreement summary
        success, summary_filename = self.save_agreement_summary(
            agreement_id, data, coordinator_name, student_filename, equipment_list
        )

        # Checkout equipment
        student_id = data.get('student_id')
        checkout_results = self.checkout_equipment(student_id, equipment_list)

        # Log the submission
        logger.info(f"VIP user {user_info.get('name')} submitted loan agreement for {borrower_name}")
        log_security_event("LOAN_AGREEMENT_SUBMITTED",
                         f"Loan agreement {agreement_id} submitted for {borrower_name} - "
                         f"Equipment: {equipment_summary} - "
                         f"Checkouts: {checkout_results['successful_count']} successful, "
                         f"{checkout_results['failed_count']} failed",
                         user_id)

        # Prepare response
        response_data = {
            'success': True,
            'message': f'Loan agreement successfully submitted for {borrower_name}',
            'agreement_id': agreement_id,
            'signatures_saved': True,
            'files': {
                'student_signature': student_filename,
                'summary': summary_filename
            },
            'checkout_results': checkout_results
        }

        return True, response_data


# Singleton instance
loan_agreement_service = LoanAgreementService()
