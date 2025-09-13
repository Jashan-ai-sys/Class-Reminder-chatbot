import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
load_dotenv()


FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise RuntimeError("❌ Set FERNET_KEY env var (use Fernet.generate_key())")

fernet = Fernet(FERNET_KEY)


def encrypt_password(password: str) -> bytes:
    """Encrypt password into bytes for safe DB storage."""
    return fernet.encrypt(password.encode())


def decrypt_password(enc: bytes) -> str:
    """Decrypt password from bytes back into string."""
    return fernet.decrypt(enc).decode()
