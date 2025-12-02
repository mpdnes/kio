#!/usr/bin/env python3
"""
Secure storage utilities for sensitive data handling
"""
import os
import hashlib
import json
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging

logger = logging.getLogger(__name__)

class SecureStorage:
    """Handle encrypted storage of sensitive data"""
    
    def __init__(self, storage_dir='/var/www/kiosk/secure_data'):
        self.storage_dir = storage_dir
        self.signatures_dir = os.path.join(storage_dir, 'signatures')
        self.metadata_dir = os.path.join(storage_dir, 'metadata')
        
        # Ensure directories exist with proper permissions
        os.makedirs(self.signatures_dir, mode=0o700, exist_ok=True)
        os.makedirs(self.metadata_dir, mode=0o700, exist_ok=True)
        
    def _get_encryption_key(self):
        """
        Retrieve encryption key from environment with persistent fallback

        CRITICAL: This key must be set in production via SENSITIVE_DATA_ENCRYPTION_KEY
        environment variable. Without it, encrypted data cannot be recovered.
        """
        key_env = os.getenv('SENSITIVE_DATA_ENCRYPTION_KEY')
        if not key_env:
            logger.error("CRITICAL: SENSITIVE_DATA_ENCRYPTION_KEY not set in environment!")
            logger.error("Encrypted data will be UNRECOVERABLE without this key!")
            raise RuntimeError(
                "SENSITIVE_DATA_ENCRYPTION_KEY must be set in environment. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        return key_env.encode()
    
    def _encrypt_data(self, data):
        """Encrypt data using Fernet symmetric encryption"""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.encrypt(data)
    
    def _decrypt_data(self, encrypted_data):
        """Decrypt data using Fernet symmetric encryption"""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data)
    
    def _generate_secure_filename(self, student_id, agreement_id, file_type='signature'):
        """Generate secure, anonymized filename"""
        # Create hash of student_id + agreement_id for uniqueness without PII
        hash_input = f"{student_id}_{agreement_id}_{file_type}".encode()
        file_hash = hashlib.sha256(hash_input).hexdigest()[:16]
        timestamp = int(datetime.now().timestamp())
        return f"SA_{timestamp}_{file_hash}.enc"
    
    def store_signature(self, signature_data, student_id, agreement_id, metadata=None):
        """
        Store signature securely with encryption
        
        Args:
            signature_data: Binary signature image data
            student_id: User ID (for generating secure filename)
            agreement_id: Loan agreement ID
            metadata: Additional metadata (sanitized)
        
        Returns:
            str: Secure file identifier for retrieval
        """
        try:
            # Generate secure filename
            filename = self._generate_secure_filename(student_id, agreement_id)
            file_path = os.path.join(self.signatures_dir, filename)
            
            # Encrypt signature data
            encrypted_data = self._encrypt_data(signature_data)
            
            # Store encrypted file
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions
            os.chmod(file_path, 0o600)
            
            # Store metadata separately (also encrypted)
            if metadata:
                metadata['created_at'] = datetime.now().isoformat()
                metadata['retention_expires'] = (datetime.now() + timedelta(days=2555)).isoformat()  # 7 years
                metadata_json = json.dumps(metadata).encode()
                encrypted_metadata = self._encrypt_data(metadata_json)
                
                metadata_path = os.path.join(self.metadata_dir, f"{filename}.meta")
                with open(metadata_path, 'wb') as f:
                    f.write(encrypted_metadata)
                os.chmod(metadata_path, 0o600)
            
            logger.info(f"Securely stored signature with ID: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to store signature securely: {e}")
            raise
    
    def retrieve_signature(self, file_identifier):
        """
        Retrieve and decrypt signature file
        
        Args:
            file_identifier: Secure file identifier from store_signature
        
        Returns:
            bytes: Decrypted signature data
        """
        try:
            file_path = os.path.join(self.signatures_dir, file_identifier)
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Signature file not found: {file_identifier}")
            
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            return self._decrypt_data(encrypted_data)
            
        except Exception as e:
            logger.error(f"Failed to retrieve signature {file_identifier}: {e}")
            raise
    
    def cleanup_expired_data(self):
        """Remove data past retention period (FERPA compliance)"""
        try:
            current_time = datetime.now()
            deleted_count = 0
            
            for metadata_file in os.listdir(self.metadata_dir):
                if not metadata_file.endswith('.meta'):
                    continue
                    
                metadata_path = os.path.join(self.metadata_dir, metadata_file)
                
                try:
                    with open(metadata_path, 'rb') as f:
                        encrypted_metadata = f.read()
                    
                    decrypted_metadata = self._decrypt_data(encrypted_metadata)
                    metadata = json.loads(decrypted_metadata.decode())
                    
                    expire_date = datetime.fromisoformat(metadata.get('retention_expires', ''))
                    
                    if current_time > expire_date:
                        # Delete signature file
                        signature_file = metadata_file.replace('.meta', '')
                        signature_path = os.path.join(self.signatures_dir, signature_file)
                        
                        if os.path.exists(signature_path):
                            os.remove(signature_path)
                        os.remove(metadata_path)
                        
                        deleted_count += 1
                        logger.info(f"Deleted expired signature: {signature_file}")
                        
                except Exception as e:
                    logger.error(f"Error processing metadata file {metadata_file}: {e}")
                    continue
            
            logger.info(f"Data retention cleanup completed. Deleted {deleted_count} expired files.")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            raise

# Global instance
secure_storage = SecureStorage()