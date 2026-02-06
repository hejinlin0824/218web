from cryptography.fernet import Fernet
import base64
from django.conf import settings

class EncryptionManager:
    """
    使用 Django 的 SECRET_KEY 作为种子进行加密解密
    """
    def __init__(self):
        # 确保 key 是 32 url-safe base64-encoded bytes
        key = settings.SECRET_KEY[:32].encode() 
        # 如果 SECRET_KEY 不够长，补齐 (仅作演示，生产环境建议配置专门的 ENCRYPT_KEY)
        key = base64.urlsafe_b64encode(key.ljust(32)[:32])
        self.cipher = Fernet(key)

    def encrypt(self, text):
        if not text: return None
        return self.cipher.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        if not encrypted_text: return None
        try:
            return self.cipher.decrypt(encrypted_text.encode()).decode()
        except Exception:
            return None