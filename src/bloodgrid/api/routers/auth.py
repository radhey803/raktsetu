"""
BloodGrid Authentication & API Key Management Router
=====================================================
Handles user registration, argon2 password verification, JWT issuance,
and developer API key generation with SHA-256 hashed storage.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
import jwt

from bloodgrid.api.deps import get_request_id, verify_api_key_or_jwt
from bloodgrid.api.schemas.meta import (
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    AuthTokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from bloodgrid.config import settings

router = APIRouter(prefix="/v1/auth", tags=["Authentication & Developer API Keys"])
hasher = PasswordHasher()

# In-memory mock store for app state when PostgreSQL is not connected locally
_LOCAL_USERS_DB: Dict[str, dict] = {}
_LOCAL_API_KEYS_DB: Dict[str, dict] = {}


def create_jwt_tokens(user_id: str, email: str, tier: str = "pro") -> AuthTokenResponse:
    now = datetime.now(timezone.utc)
    expire_access = now + timedelta(minutes=settings.jwt_expire_minutes)
    expire_refresh = now + timedelta(days=30)

    access_payload = {
        "sub": user_id,
        "email": email,
        "tier": tier,
        "exp": expire_access,
        "iat": now,
        "type": "access"
    }
    refresh_payload = {
        "sub": user_id,
        "exp": expire_refresh,
        "iat": now,
        "type": "refresh"
    }

    access_token = jwt.encode(access_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    refresh_token = jwt.encode(refresh_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_minutes=settings.jwt_expire_minutes
    )


@router.post("/register", summary="Create User Account")
def register_user(req: UserRegisterRequest):
    email = req.email.lower().strip()
    if email in _LOCAL_USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists"
        )

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    pwd_hash = hasher.hash(req.password)

    _LOCAL_USERS_DB[email] = {
        "user_id": user_id,
        "email": email,
        "full_name": req.full_name,
        "organization": req.organization_name,
        "password_hash": pwd_hash,
        "tier": "community",
        "created_at": datetime.now(timezone.utc)
    }

    tokens = create_jwt_tokens(user_id=user_id, email=email, tier="community")
    return {
        "success": True,
        "user": {
            "id": user_id,
            "email": email,
            "full_name": req.full_name,
            "tier": "community"
        },
        "tokens": tokens
    }


@router.post("/login", summary="User Login & JWT Issuance")
def login_user(req: UserLoginRequest):
    email = req.email.lower().strip()
    user = _LOCAL_USERS_DB.get(email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    try:
        hasher.verify(user["password_hash"], req.password)
    except VerifyMismatchError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    tokens = create_jwt_tokens(user_id=user["user_id"], email=email, tier=user["tier"])
    return {
        "success": True,
        "user": {
            "id": user["user_id"],
            "email": email,
            "full_name": user["full_name"],
            "tier": user["tier"]
        },
        "tokens": tokens
    }


@router.post("/api-keys", summary="Generate New API Key")
def generate_api_key(
    req: ApiKeyCreateRequest,
    auth: dict = Depends(verify_api_key_or_jwt)
):
    """
    Issues a new API key. The unhashed raw secret is displayed ONCE and cannot be recovered.
    """
    key_id = f"bg_live_{secrets.token_hex(4)}"
    raw_secret = f"{key_id}_{secrets.token_urlsafe(24)}"
    secret_hash = hashlib.sha256(raw_secret.encode()).hexdigest()

    tier_rate_limits = {
        "pro": settings.rate_limit_pro,
        "developer": settings.rate_limit_enterprise,
        "organization": "5000/minute"
    }
    rate_limit = tier_rate_limits.get(req.tier, settings.rate_limit_public)

    now_dt = datetime.now(timezone.utc)
    _LOCAL_API_KEYS_DB[key_id] = {
        "key_id": key_id,
        "key_name": req.key_name,
        "secret_hash": secret_hash,
        "tier": req.tier,
        "rate_limit": rate_limit,
        "created_at": now_dt,
        "is_active": True
    }

    return {
        "success": True,
        "key_id": key_id,
        "key_name": req.key_name,
        "api_key_secret": raw_secret,
        "tier": req.tier,
        "rate_limit": rate_limit,
        "created_at": now_dt.isoformat(),
        "warning": "Copy your API key now. It will not be shown again."
    }


@router.get("/api-keys", summary="List Active API Keys")
def list_api_keys(auth: dict = Depends(verify_api_key_or_jwt)):
    keys = [
        {
            "key_id": k["key_id"],
            "key_name": k["key_name"],
            "tier": k["tier"],
            "rate_limit": k["rate_limit"],
            "created_at": k["created_at"].isoformat(),
            "is_active": k["is_active"]
        }
        for k in _LOCAL_API_KEYS_DB.values()
    ]
    return {"success": True, "keys": keys}
