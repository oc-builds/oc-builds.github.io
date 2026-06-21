"""Pydantic v2 models for the API surface.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

Why Pydantic at the API boundary: the original notebook accepted whatever
shape the caller passed and shoved it into Mongo. Validation here gives us
two things at once -- a typed contract that FastAPI turns into OpenAPI
schemas (the Outcome 1 interface artifact) and a hard rejection of malformed
input before it reaches the database. The collection itself ALSO has a
$jsonSchema validator applied by db_setup.py, so we have validation at both
the API and the data tier.

Note on optional fields: `name` is populated in ~70% of the real 10k rows
and `outcome_subtype` in ~46%. Modeling those as Optional matches reality
and is one of the explicit reasons the narrative cites for staying on Mongo
rather than migrating to a relational schema.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Role(str, Enum):
    """Application-side roles. Enforced by the JWT layer at runtime.

    Mongo-side roles with the same names are created by db_setup.py for
    operator/shell access. See auth.py for the honest framing.
    """

    ADMIN = "admin"
    STAFF = "staff"
    VIEWER = "viewer"


class RescueCategory(str, Enum):
    """The four filters the original dashboard exposed. `RESET` from the
    notebook is not a category -- it was a UI affordance -- so it is omitted
    here. The mapping from category to (breed, sex, age) constraints lives
    in crud.py because it is a query-construction concern.
    """

    WATER = "Water"
    MOUNTAIN = "Mountain"
    DISASTER = "Disaster"


# ---------------------------------------------------------------------------
# GeoJSON
# ---------------------------------------------------------------------------


class GeoPoint(BaseModel):
    """GeoJSON Point. Mongo's 2dsphere index requires this exact shape.

    Why [lon, lat] and not [lat, lon]: GeoJSON spec is x-then-y, which means
    longitude first. The original notebook stored two scalar columns and the
    Leaflet marker read lat from column 13 and long from column 14 by index
    -- the migration script is the place where we flip into GeoJSON order
    once, with explicit range assertions, so this model can trust the input.
    """

    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(..., min_length=2, max_length=2)

    @field_validator("coordinates")
    @classmethod
    def _validate_lon_lat(cls, v: list[float]) -> list[float]:
        lon, lat = v[0], v[1]
        if not -180.0 <= lon <= 180.0:
            raise ValueError(f"longitude {lon} out of range [-180, 180]")
        if not -90.0 <= lat <= 90.0:
            raise ValueError(f"latitude {lat} out of range [-90, 90]")
        return v


# ---------------------------------------------------------------------------
# Animals
# ---------------------------------------------------------------------------


class AnimalBase(BaseModel):
    """Shared fields between create/update/read views of an animal.

    `name` and `outcome_subtype` are Optional because the real data is sparse
    in those columns. Modeling that explicitly is the polyglot-positioning
    point the narrative lands.
    """

    model_config = ConfigDict(extra="forbid")

    animal_id: str = Field(..., description="Austin Animal Center identifier")
    animal_type: str
    breed: str
    color: Optional[str] = None
    name: Optional[str] = None
    sex_upon_outcome: Optional[str] = None
    age_upon_outcome: Optional[str] = None
    age_upon_outcome_in_weeks: Optional[float] = None
    outcome_type: Optional[str] = None
    outcome_subtype: Optional[str] = None
    date_of_birth: Optional[str] = None
    datetime: Optional[str] = None
    monthyear: Optional[str] = None
    location: GeoPoint


class Animal(AnimalBase):
    """Read-side representation. `_id` is rendered as `id` for JSON callers."""

    id: Optional[str] = Field(default=None, alias="_id")
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class AnimalCreate(AnimalBase):
    """Create-side payload. Identical to AnimalBase today; kept as a separate
    name so future create-only fields (e.g. created_by) do not leak into the
    read model.
    """


class AnimalUpdate(BaseModel):
    """Patch-style update. Every field optional so a partial update is legal.

    Why a separate model rather than reusing AnimalBase with all-optional:
    AnimalBase has required fields by design (animal_id, breed, location).
    A PUT/PATCH should be able to omit those and still be valid.
    """

    model_config = ConfigDict(extra="forbid")

    animal_type: Optional[str] = None
    breed: Optional[str] = None
    color: Optional[str] = None
    name: Optional[str] = None
    sex_upon_outcome: Optional[str] = None
    age_upon_outcome: Optional[str] = None
    age_upon_outcome_in_weeks: Optional[float] = None
    outcome_type: Optional[str] = None
    outcome_subtype: Optional[str] = None
    date_of_birth: Optional[str] = None
    datetime: Optional[str] = None
    monthyear: Optional[str] = None
    location: Optional[GeoPoint] = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """POST /auth/login body.

    Min length 8 on password matches the Outcome 5 security checklist and
    is enforced at the API boundary so a weak password is rejected before
    bcrypt ever sees it.
    """

    model_config = ConfigDict(extra="forbid")

    username: Annotated[str, Field(min_length=1, max_length=64)]
    password: Annotated[str, Field(min_length=8, max_length=128)]


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class User(BaseModel):
    """Stored user document, minus the password hash. Never returned with
    the hash attached -- the hash lives only in the database write path.
    """

    model_config = ConfigDict(extra="forbid")

    username: str
    role: Role


class UserCreate(BaseModel):
    """Admin-only registration payload (see routes_auth.py)."""

    model_config = ConfigDict(extra="forbid")

    username: Annotated[str, Field(min_length=1, max_length=64)]
    password: Annotated[str, Field(min_length=8, max_length=128)]
    role: Role


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class AuditEntry(BaseModel):
    """Schema for audit_log documents. See audit.py for the writer and the
    redaction rules applied before this is persisted.
    """

    model_config = ConfigDict(extra="forbid")

    user: str
    action: str
    target_collection: str
    target_id: Optional[str] = None
    timestamp: datetime
    before: Optional[dict[str, Any]] = None
    after: Optional[dict[str, Any]] = None
