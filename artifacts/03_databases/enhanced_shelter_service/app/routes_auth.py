"""Auth routes: /auth/login and /auth/register.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

/auth/login is rate-limited via slowapi to slow down credential stuffing.
/auth/register is locked to admin role only -- this service is internal
(shelter staff, intake clerks, partner-rescue auditors), so open
self-registration would be a footgun. The original notebook had no
registration story at all; pinning this to admin is a deliberate Outcome 5
hardening.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from .auth import (
    create_access_token,
    hash_password,
    require_role,
    verify_password,
)
from .config import settings
from .db import Repository
from .models import LoginRequest, Role, Token, User, UserCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# slowapi limiter. The actual limiter instance is also attached to the app
# in main.py so the SlowAPIMiddleware can see it; sharing here keeps the
# route decorators self-contained.
limiter = Limiter(key_func=get_remote_address)


def _get_repo(request: Request) -> Repository:
    """Pull the Repository the lifespan stashed onto app.state."""
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="repository not initialized",
        )
    return repo


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest) -> Token:
    """Verify credentials and mint a bearer token."""
    repo = _get_repo(request)
    user_doc = repo.find_user(body.username)
    if not user_doc or not verify_password(body.password, user_doc.get("password_hash", "")):
        # Same error for unknown-user and bad-password so an attacker
        # cannot enumerate valid usernames.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    role = Role(user_doc["role"])
    token, expires_in = create_access_token(subject=body.username, role=role)
    return Token(access_token=token, expires_in=expires_in)


@router.post(
    "/register",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: Request,
    body: UserCreate,
    current: User = Depends(require_role(Role.ADMIN)),
) -> User:
    """Admin-only registration. Routes through the chokepoint so the new
    user creation is journaled to audit_log just like any other write.
    """
    repo = _get_repo(request)
    if repo.find_user(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="username already exists",
        )
    repo.save_with_audit(
        user=current.username,
        action="register_user",
        collection_name=settings.users_collection,
        target_id=body.username,
        operation="insert",
        payload={
            "username": body.username,
            "password_hash": hash_password(body.password),
            "role": body.role.value,
        },
    )
    return User(username=body.username, role=body.role)
