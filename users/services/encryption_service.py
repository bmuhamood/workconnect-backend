from cryptography.fernet import Fernet
from django.conf import settings
import base64


class EncryptionService:
    """Service for encrypting sensitive data"""
    
    def __init__(self):
        # Ensure encryption key is properly padded
        key = settings.ENCRYPTION_KEY.encode()
        if len(key) < 32:
            # Pad with zeros
            key = key.ljust(32, b'0')
        elif len(key) > 32:
            # Truncate
            key = key[:32]
        
        # Convert to base64
        key_b64 = base64.urlsafe_b64encode(key)
        self.cipher = Fernet(key_b64)
    
    def encrypt(self, data):
        """
        Encrypt data
        """
        if isinstance(data, str):
            data = data.encode()
        return self.cipher.encrypt(data)
    
    def decrypt(self, encrypted_data):
        """
        Decrypt data
        """
        decrypted = self.cipher.decrypt(encrypted_data)
        return decrypted.decode()
