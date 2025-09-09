from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.hash import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session
from .config import settings
from .models import UserDB
from .db import get_session

# Password hashing


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.verify(password, password_hash)


# JWT

bearer_scheme = HTTPBearer(auto_error=False)


def create_token(user_id: str, email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.auth_token_ttl_min)
    payload = {"sub": user_id, "email": email, "exp": exp}
    return jwt.encode(payload, settings.auth_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.auth_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    s: Session = Depends(get_session),
) -> Optional[UserDB]:
    if not creds:
        return None
    token = creds.credentials
    data = decode_token(token)
    user = s.get(UserDB, data["sub"])
    if not user:
        raise HTTPException(401, "User not found")
    return user
