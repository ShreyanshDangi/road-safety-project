# shared/auth.py

import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

try:
    from jose import JWTError, jwt
except ImportError:
    raise ImportError("Run: pip install python-jose[cryptography]")

SECRET_KEY          = os.getenv("JWT_SECRET", "fallback-secret-change-this")
ALGORITHM           = "HS256"
TOKEN_EXPIRE_HOURS  = 8

AUTHORITY_USERNAME  = os.getenv("AUTHORITY_USERNAME", "admin")
AUTHORITY_PASSWORD  = os.getenv("AUTHORITY_PASSWORD", "roadsafety2026")


def create_token(username: str) -> str:
    expire  = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str | None:
    """Returns username if token is valid, None otherwise."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def check_credentials(username: str, password: str) -> bool:
    return username == AUTHORITY_USERNAME and password == AUTHORITY_PASSWORD