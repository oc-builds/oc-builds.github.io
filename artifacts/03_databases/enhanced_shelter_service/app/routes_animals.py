"""Animal routes. The HTTP surface of the application.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

Layering: routes parse Pydantic, look up the repository on app.state, and
delegate everything else to crud.py. There is NO direct PyMongo use in
this file. That separation is what lets crud.py be tested with mongomock
without TestClient and lets routes be tested with TestClient without
hitting the live database in some tests.

Role mapping:
  - viewer  : GET endpoints only
  - staff   : GET + POST + PUT
  - admin   : GET + POST + PUT + DELETE (delete is admin-exclusive)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from . import crud
from .auth import get_current_user, require_role
from .config import settings
from .db import Repository
from .models import (
    Animal,
    AnimalCreate,
    AnimalUpdate,
    RescueCategory,
    Role,
    User,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/animals", tags=["animals"])


def _get_repo(request: Request) -> Repository:
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="repository not initialized",
        )
    return repo


def _repo_for_user(request: Request, user: User) -> Repository:
    """Return the Repository bound to this caller's role-scoped DB pool.

    M7 DB-tier isolation: when the lifespan installed a ClientFactory, we ask
    it for a Repository whose underlying MongoClient authenticates with the
    role-matched Mongo credential. That makes the database itself a second
    enforcement tier behind the JWT require_role checks. When NO factory is
    present (the TestClient path sets app.state.repository directly and skips
    the lifespan, and the fallback deployment mode), we degrade cleanly to the
    single shared repository. Either way the JWT-layer checks already ran on
    the route, so this never loosens a control.
    """
    factory = getattr(request.app.state, "client_factory", None)
    if factory is not None:
        return factory.repository_for_role(user.role)
    return _get_repo(request)


# ---------------------------------------------------------------------------
# Read endpoints (any authenticated role)
# ---------------------------------------------------------------------------


@router.get("", response_model=list[dict])
def list_animals(
    request: Request,
    breed: Optional[str] = None,
    sex: Optional[str] = None,
    rescue: Optional[RescueCategory] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    repo = _repo_for_user(request, user)
    return crud.list_animals(
        repo,
        breed=breed,
        sex=sex,
        rescue=rescue,
        skip=skip,
        limit=limit,
    )


@router.get("/near", response_model=list[dict])
def find_near(
    request: Request,
    lon: float = Query(..., ge=-180, le=180),
    lat: float = Query(..., ge=-90, le=90),
    km: float = Query(..., gt=0, le=20000),
    limit: int = Query(50, ge=1, le=500),
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    repo = _repo_for_user(request, user)
    return crud.find_near(
        repo,
        lon=lon,
        lat=lat,
        max_meters=km * 1000.0,
        limit=limit,
    )


@router.get("/aggregates/by-breed", response_model=list[dict])
def aggregates_by_breed(
    request: Request,
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    repo = _repo_for_user(request, user)
    return crud.aggregate_by_breed(repo)


@router.get("/{animal_id}", response_model=dict)
def get_animal(
    request: Request,
    animal_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    repo = _repo_for_user(request, user)
    doc = crud.get_animal(repo, animal_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="animal not found",
        )
    return doc


# ---------------------------------------------------------------------------
# Write endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
def create_animal(
    request: Request,
    payload: AnimalCreate,
    current: User = Depends(require_role(Role.ADMIN, Role.STAFF)),
) -> dict[str, Any]:
    repo = _repo_for_user(request, current)
    return crud.create_animal(
        repo,
        payload,
        user=current.username,
        collection_name=settings.animals_collection,
    )


@router.put("/{animal_id}", response_model=dict)
def update_animal(
    request: Request,
    animal_id: str,
    patch: AnimalUpdate,
    current: User = Depends(require_role(Role.ADMIN, Role.STAFF)),
) -> dict[str, Any]:
    repo = _repo_for_user(request, current)
    try:
        result = crud.update_animal(
            repo,
            animal_id,
            patch,
            user=current.username,
            collection_name=settings.animals_collection,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if result.get("matched", 0) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="animal not found",
        )
    return result


@router.delete("/{animal_id}", response_model=dict)
def delete_animal(
    request: Request,
    animal_id: str,
    current: User = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    repo = _repo_for_user(request, current)
    result = crud.delete_animal(
        repo,
        animal_id,
        user=current.username,
        collection_name=settings.animals_collection,
    )
    if result.get("deleted", 0) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="animal not found",
        )
    return result
