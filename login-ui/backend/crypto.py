import os
from cryptography.fernet import Fernet

FERNET_KEY = os.environ["FERNET_KEY"]
if not FERNET_KEY:
    raise RuntimeError("❌ Set FERNET_KEY env var (use Fernet.generate_key())")

fernet = Fernet(FERNET_KEY)

def encrypt_password(password: str) -> bytes:
    return fernet.encrypt(password.encode())

def decrypt_password(token: bytes) -> str:
    return fernet.decrypt(token).decode()
