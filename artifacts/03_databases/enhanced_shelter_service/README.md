# CS340 Enhanced Shelter -- CS499 Enhancement Three

MongoDB-backed shelter service. CS499 rebuild of the CS340 Austin Animal
Center project (`CRUD_Python_Module.py` + `ProjectTwoDashboard.ipynb`).

**Author:** Sanjay Chauhan
**Course:** CS499 Computer Science Capstone
**Category:** Databases
**Date:** 2026-06-07

The original was a PyMongo CRUD class plus a Jupyter Dash notebook that
loaded all 10,000 outcome records into memory at startup, embedded
credentials in source, had no schema validation, no indexes, no audit
log, and no role separation. This rebuild keeps MongoDB and replaces the
notebook with a FastAPI service that adds JSON Schema validation, a
compound index plus a 2dsphere geospatial index, JWT auth with three
roles, bcrypt password hashing, a single-writer audit log, and an
auto-generated OpenAPI contract at `/docs`.

The architecture plan that drove this build lives at
`../../M5/Milestone Four/Enhancement_Three_Architecture_Plan.md` in the
course tree.

---

## The OpenAPI document is the working product

Once the service is running, the interactive interface contract is at:

- **Swagger UI:** http://localhost:8000/docs
- **OpenAPI JSON:** http://localhost:8000/openapi.json

A grader can log in via the "Authorize" button, hit every endpoint, see
the Pydantic schemas inline, and inspect example responses. No frontend
needed for the milestone (a React UI is planned for the M7 polish phase).

---

## Two run paths

### Path 1: Canonical -- docker-compose + uvicorn

This is the path the milestone is graded against. It exercises the
$jsonSchema validator, the 2dsphere index, the aggregation pipeline, and
the Mongo-side roles -- the features mongomock cannot run.

```bash
# 1. Configure env
cp .env.example .env
# Edit .env: at minimum, change JWT_SECRET to a long random string.
# python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Bring up MongoDB 7
docker compose up -d

# 3. Install Python deps
pip install -e ".[dev]"

# 4. Apply $jsonSchema, indexes, and Mongo-side roles
python3 scripts/db_setup.py

# 5. (Optional but recommended) Migrate the original 10k animals collection
#    to animals_geo with GeoJSON coordinates. Safe to skip if you only want
#    to play with seeded fixture data.
python3 scripts/migrate_geojson.py

# 6. Seed demo users (admin/staff/viewer) and a 200-row fixture from the CSV
python3 scripts/seed.py

# 7. Run the API
uvicorn app.main:app --reload --port 8000

# 8. Open http://localhost:8000/docs and click "Authorize"
```

#### Demo credentials (GRADING ONLY)

These are committed on purpose so a grader can sign in without a separate
credential exchange. Rotate them before any non-grading use.

| Username | Password         | Role   |
|----------|------------------|--------|
| admin    | `Admin#Demo2026!`  | admin  |
| staff    | `Staff#Demo2026!`  | staff  |
| viewer   | `Viewer#Demo2026!` | viewer |

### Path 2: Tests via mongomock (CI-style verification)

mongomock does NOT implement the $jsonSchema validator, 2dsphere indexes,
or several aggregation operators. The test suite is split accordingly:

- `tests/test_crud_shape.py` -- CRUD chokepoint + audit log redaction +
  Pydantic validation + JWT round-trip, all under mongomock.
- `tests/test_specs.py` -- pure spec assertions on the validator dict, the
  compound index ordering, the 2dsphere index spec, the aggregation
  pipeline shape, and the Mongo-side role specs. Verifies the dicts that
  `db_setup.py` passes to real Mongo are correct without needing to run
  them.
- `tests/test_routes.py` -- FastAPI TestClient against mongomock. Verifies
  login, RBAC (401 vs 403 vs 200), admin-only DELETE, etc.

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Quickstart curl examples

```bash
# Log in (admin)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin#Demo2026!"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# List animals (any role)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/animals?limit=5"

# Filter by rescue category
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/animals?rescue=Water&limit=5"

# Proximity query (lon, lat, radius in km)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/animals/near?lon=-97.74&lat=30.27&km=10&limit=5"

# Aggregation: count by breed
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/animals/aggregates/by-breed" | head

# Create (admin or staff)
curl -s -X POST http://localhost:8000/animals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"animal_id":"A999001","animal_type":"Dog","breed":"Labrador Retriever Mix","location":{"type":"Point","coordinates":[-97.74,30.27]}}'

# Delete (admin only)
curl -s -X DELETE http://localhost:8000/animals/A999001 \
  -H "Authorization: Bearer $TOKEN"
```

---

## Hardening (Module 7)

Three optional defense-in-depth changes were layered on top of the graded
M5/M6 build. None of them alter the existing API behavior; each adds a tier
of enforcement or a query path and degrades gracefully when its deployment
prerequisites are absent. All prior tests still pass and new tests were
added (45 total, up from 30).

### 1. Database-side audit enforcement (change-stream watcher)

**Why.** The audit guarantee rested entirely on the
`Repository.save_with_audit()` Python chokepoint. Any write made *directly*
against MongoDB (a `mongosh` session, a stray PyMongo script) bypasses it and
leaves no audit trail -- the existing negative test
`test_direct_write_does_not_produce_audit_entry` proves that gap exists.

**What.** `scripts/audit_watcher.py` opens a MongoDB **change stream** on
`animals_geo`. For every insert/update/replace/delete it checks whether a
matching `audit_log` entry already exists (i.e. the chokepoint recorded it);
if not, it writes a catch-up entry tagged `source="change_stream_watcher"`
and `user="<unknown:direct-db-write>"`. Result: every state change to
`animals_geo` lands in `audit_log`, whether it went through the API or around
it.

**Honest limitation.** A true server-side trigger requires MongoDB Atlas
Triggers / Realm, which is not available self-hosted. The change-stream
consumer is the self-hostable equivalent. It is **eventually consistent**,
not transactional -- there is a small window between the operational write
and the catch-up audit entry. Correlation against existing chokepoint entries
is best-effort by `(target_collection, target_id)` within a short time window
(documented in the module).

**Deployment requirement.** Change streams require the `mongod` to run as a
**replica set** (even single-node). The default `docker-compose.yml` runs a
standalone Mongo, which does *not* emit change streams. To enable:

```bash
# Run mongod as a single-node replica set, then initiate it once:
docker compose run --rm mongo mongod --replSet rs0  # or add command: to compose
mongosh --eval 'rs.initiate()'
python3 scripts/audit_watcher.py            # leave running as a sidecar
```

**Verification.** The pure decision logic (`needs_catch_up_audit`) and the
per-event handler (`_handle_change`, `_extract_target_id`) are unit-tested
against mongomock in `tests/test_audit_watcher.py` (8 tests). The streaming
loop itself is verified only on a live replica set, because mongomock cannot
emit a change stream -- this is stated rather than faked.

### 2. DB-tier isolation (per-role connection pools)

**Why.** The app connected to Mongo with one service-account credential for
every request; runtime RBAC lived only at the JWT layer (auth.py is explicit
about this). A bug that slipped a write past `require_role` would still
succeed at the database.

**What.** `app/db_provider.py` adds a `ClientFactory` that owns one pooled
`MongoClient` **per role** and hands each request a `Repository` bound to the
role-appropriate pool, selected from the JWT role. `scripts/db_setup.py` now
provisions three Mongo users (`aac_admin`/`aac_staff`/`aac_viewer`) bound to
the operator roles it already created, so a viewer credential can only
`find`, staff can `find/insert/update` but not `remove`, and admin can do
everything. With this enabled, a viewer-scoped request that somehow reached a
write path would also fail at Mongo, not just at the JWT check. **The JWT
`require_role` checks are unchanged and always active** (defense in depth).

**Graceful fallback.** Provisioning three Mongo users is a deployment step.
If `MONGO_URI_ADMIN/STAFF/VIEWER` are not set, every role resolves to the
single `MONGO_URI` service account -- exactly the baseline. `db_setup.py`
skips user creation when the password env vars are absent (no default
passwords are ever written). So a grader who runs the project as-is gets the
original working behavior; the isolation tier activates only when configured.

**Verification.** `tests/test_db_provider.py` (5 tests) covers URI resolution
(role-specific vs fallback), pool-per-distinct-URI accounting (one pool in
fallback, three when isolated), pool reuse, and that the returned Repository
is usable. The factory takes injectable `client_maker`/`uri_resolver` so no
live Mongo or three-user setup is needed for the unit tests.

### 3. Compound 2dsphere index for filtered proximity queries

**Why.** The `/animals/near` rescue use case is rarely "any animal near a
point" -- it is "Water-rescue Labradors near this flood zone", i.e.
`$nearSphere` on `location` *plus* equality filters on `breed`/`sex`. With
only the single-field 2dsphere index, Mongo uses the index for the geo term
but then fetch-and-filters every candidate for breed/sex.

**What.** `db_setup.py` adds `GEO_COMPOUND_INDEX_SPEC =
[(location, 2dsphere), (breed, ASC), (sex_upon_outcome, ASC)]`. The 2dsphere
field is placed **first** because our access pattern uses geo as the leading
discriminator and breed/sex as trailing equality bounds; this lets the
planner satisfy the `$nearSphere` on the leading key and apply breed/sex as
index bounds rather than post-filtering. The original single-field 2dsphere
index is **kept** (bare proximity and `$geoWithin`/`$geoIntersects` still
prefer it); both coexist and the planner picks per query.

**Verification.** mongomock cannot build or plan a 2dsphere index, so the
spec is asserted in `tests/test_specs.py`
(`test_geo_compound_index_leads_with_2dsphere_then_breed_sex`) and exercised
for real only on the docker-compose path -- the same testing split the
project already uses for the existing 2dsphere and aggregation features.

---

## File map

```
docker-compose.yml         Mongo 7 with persistent volume
.env.example               Required env vars (fail-fast on missing)
pyproject.toml             Deps + pytest config
app/
  config.py                Settings dataclass; raises RuntimeError if env missing
  db.py                    Repository chokepoint -- the ONLY write path
  models.py                Pydantic v2 models (Animal, GeoPoint, LoginRequest, ...)
  auth.py                  bcrypt + JWT (HS256 pinned, 8h TTL); require_role()
  audit.py                 AuditWriter with redaction (password|token|secret)
  crud.py                  list/get/create/update/delete + near + aggregate
  db_provider.py           M7: role-scoped ClientFactory (DB-tier isolation)
  routes_auth.py           /auth/login (rate-limited), /auth/register (admin)
  routes_animals.py        /animals CRUD + /near + /aggregates/by-breed
  main.py                  FastAPI app + lifespan + exception handler
scripts/
  db_setup.py              $jsonSchema + indexes (incl. M7 compound 2dsphere)
                           + Mongo-side roles + M7 per-role Mongo users
  audit_watcher.py         M7: change-stream sidecar back-filling missing audits
  migrate_geojson.py       Two-pass copy animals -> animals_geo with [lon, lat]
  seed.py                  Demo users + 200-row CSV fixture
tests/
  conftest.py              mongomock + env setup
  test_crud_shape.py       CRUD chokepoint, audit, Pydantic, JWT (mongomock)
  test_specs.py            Pure spec assertions (no Mongo execution required)
  test_routes.py           FastAPI TestClient + mongomock
  test_db_provider.py      M7: ClientFactory role-selection + pooling (unit)
  test_audit_watcher.py    M7: change-stream catch-up decision logic (unit)
```

---

## Course outcomes hit (quick map)

- **Outcome 1 (collaboration):** named personas in `CONTRIBUTING.md` (shelter
  manager, intake clerk, partner-rescue auditor), OpenAPI as the explicit
  interface contract between hypothetical FE/BE engineers, branching strategy
  and PR template documented.
- **Outcome 3 (algorithmic trade-offs):** compound index ordered for the
  leftmost-prefix rule of the rescue queries; 2dsphere replacing O(n)
  Haversine; explicit Big-O justifications in `crud.py` and `db_setup.py`.
- **Outcome 4 (techniques + tools):** Mongo `$jsonSchema`, 2dsphere indexes,
  aggregation pipelines, FastAPI, Pydantic v2, JWT, bcrypt.
- **Outcome 5 (security):** credentials out of source, three-layer RBAC
  (Pydantic at API boundary, JWT layer for runtime, Mongo-side roles for
  operator-tier), bcrypt cost 12, JWT HS256 pinned, audit log with
  redaction, structured error envelope, login rate-limiting via slowapi.
