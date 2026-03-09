
import bleach
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with 12 rounds."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the *hashed* password."""
    return _pwd_context.verify(plain, hashed)


def sanitize_input(text: str) -> str:
    """Strip all HTML tags and attributes from *text* using bleach."""
    return bleach.clean(
        text,
        tags=[],          # no allowed tags — strip everything
        attributes={},    # no allowed attributes
        strip=True,       # strip disallowed tags rather than escaping
        strip_comments=True,
    )
