"""Authentication: bcrypt password hashing + JWT issuance/validation.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

Honest framing on RBAC layering: runtime role enforcement in this codebase
lives at the JWT layer. The FastAPI process connects to MongoDB using a
single service-account credential (the URI from .env), so every database
operation reaches Mongo as that same identity regardless of which API
caller triggered it. The Mongo-side roles created by db_setup.py
(admin/staff/viewer) are operator-tier controls -- they govern who can
run mongosh, who can run the migration script, who can connect with a
direct PyMongo client outside the API. They are NOT the runtime path that
guards a DELETE /animals/{id} call. That guard is the require_role(ADMIN)
dependency on the route. Dr. Bolton has a database background and would
see straight through any wording that conflated the two; the narrative
states this explicitly.

Why HS256 pinned: passing `algorithms=["HS256"]` to jwt.decode is the
defense against the historic "alg=none" attack and against accidentally
accepting a different algorithm. python-jose will refuse any token whose
header advertises an algorithm not in the list.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings
from .models import Role, User

logger = logging.getLogger(__name__)


# bcrypt cost factor 12 is the project's stated minimum; passlib will throw
# if the installed bcrypt cannot handle the rounds we ask for.
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.bcrypt_rounds,
)

# tokenUrl points at the route that mints tokens. FastAPI uses it only to
# populate the OpenAPI "Authorize" button -- the actual minting happens in
# routes_auth.py.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash. Cost factor comes from settings."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt verify."""
    return _pwd_context.verify(plain, hashed)


def create_access_token(*, subject: str, role: Role) -> tuple[str, int]:
    """Mint a JWT for `subject` with `role` baked into the claims.

    Returns (token, expires_in_seconds). Why bake role into the claim rather
    than re-reading it from the users collection on every request: a token
    is a stateless credential by design, and the alternative would put a
    Mongo round-trip in front of every API call.
    """
    expires_in = settings.jwt_ttl_seconds
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_token(token: str) -> dict[str, Any]:
    """Decode a JWT, refusing any algorithm other than HS256.

    The explicit `algorithms=["HS256"]` is load-bearing -- never accept the
    library default and never accept `None` here.
    """
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
        ) from exc


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Resolve the User from a bearer token. Raises 401 on any failure."""
    claims = decode_token(token)
    username = claims.get("sub")
    role_value = claims.get("role")
    if not username or not role_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token missing required claims",
        )
    try:
        role = Role(role_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token has unknown role",
        ) from exc
    return User(username=username, role=role)


def require_role(*allowed: Role):
    """Dependency factory: only callers whose token role is in `allowed`
    may proceed. Returns the User if allowed, raises 403 otherwise.

    Why 403 not 401: the caller IS authenticated, they just do not have
    permission for this specific operation. RFC 7235 separates the two.
    """

    def _checker(current: User = Depends(get_current_user)) -> User:
        if current.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role {current.role.value!r} not permitted",
            )
        return current

    return _checker
