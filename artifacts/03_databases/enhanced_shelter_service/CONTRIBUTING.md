# Contributing

CS499 Enhancement Three -- Austin Animal Center service. This file is
deliberately not boilerplate. It is the **Outcome 1** artifact: it names
the personas the data serves, documents how a new contributor would join
the project, and ties the OpenAPI contract to how a hypothetical frontend
and backend engineer would collaborate against the same schema without
sharing a codebase.

---

## Who uses this and why -- named personas

The original CS340 project was a generic shelter dashboard. The enhanced
version makes its audiences explicit. Every endpoint exists because one
of these three personas needs a decision from it.

### Persona 1: Maria, Shelter Manager

**Decision:** Which rescue category does this incoming animal qualify for?

Maria runs the placement program at the shelter. When a healthy adult dog
arrives, she has to decide within hours whether it goes to a water
rescue, mountain rescue, or disaster response partner -- each category
takes a specific combination of breed, sex, and age range. She uses
`GET /animals?rescue=Water` (and the two siblings) to see candidates that
match the constraints the partner organizations actually use. The rescue
filter mapping in `crud.py` IS Maria's domain knowledge, preserved from
the original notebook and made queryable.

### Persona 2: Devon, Intake Clerk

**Decision:** Is this animal record correct and up to date?

Devon types in new arrivals and updates outcome records when an animal
leaves the facility. He needs `POST /animals` for new intake and
`PUT /animals/{id}` for outcome updates. He does NOT need delete -- a
typo gets corrected with PUT, not by destroying the record. His role is
`staff`, which is why the DELETE permission is locked to `admin`. The
$jsonSchema validator and the Pydantic validation are there because
Devon's typo on a field name would have silently corrupted the original
collection.

### Persona 3: Priya, Partner-Rescue Auditor

**Decision:** Were the right animals released to the right partners over
the past 90 days?

Priya works for a partner-rescue oversight body. She does not change
data, she reviews it. Her role is `viewer`, which means she gets the
GET endpoints (including the aggregation and proximity queries) but no
write capability. Crucially, she also needs the `audit_log` collection
to show who changed what and when. The audit log is not for Devon or
Maria -- it is built for Priya. The redaction rules
(`^(password|token|secret)`) exist so an auditor never accidentally sees
credentials in the journal.

---

## Branching strategy

- `main` is the integration branch and is always deployable to local.
- Short-lived feature branches off `main`:
  `feat/<topic>` (new functionality)
  `fix/<topic>` (bug fix)
  `chore/<topic>` (deps, tooling)
- One concern per branch. A branch that touches both the auth layer and
  a new aggregation endpoint should be two branches.
- Rebase before merge. No merge commits on `main`.
- Tests must pass locally (`pytest tests/`) before opening a PR.

## PR template

Copy/paste this into the PR description.

```
## Summary

What changed and why. One paragraph.

## Persona impact

Which of the three personas (Maria / Devon / Priya) is this change for?
What decision does it improve or unblock?

## Files touched

- app/...
- scripts/...
- tests/...

## Test plan

- [ ] `pytest tests/` passes locally
- [ ] Manual smoke against docker compose path (login -> CRUD -> near -> aggregate)
- [ ] Any new write endpoint passes through Repository.save_with_audit()
- [ ] New env vars (if any) added to .env.example AND README

## Security review

- [ ] No new credentials in source
- [ ] No new fields named password/token/secret leaked outside audit redaction
- [ ] If a new role check was added, the negative case (wrong role -> 403) is tested

## Outcome alignment

Which CS499 course outcome(s) does this advance? (1 / 2 / 3 / 4 / 5)
```

---

## How a new contributor onboards

1. Clone the repo. Read `README.md` first, then `CONTRIBUTING.md`
   (this file), then the architecture plan in
   `../../M5/Milestone Four/Enhancement_Three_Architecture_Plan.md`.
2. `cp .env.example .env`, generate a real `JWT_SECRET`.
3. `docker compose up -d` to get Mongo. `pip install -e ".[dev]"`.
4. `python3 scripts/db_setup.py`, then `scripts/seed.py`.
5. `uvicorn app.main:app --reload`. Open `/docs`, click Authorize, sign in
   as `admin/Admin#Demo2026!`. You should be able to GET / POST / DELETE.
6. Run `pytest tests/ -v`. All tests must pass before you touch any code.
7. Pick a small task. The first PR is read-only -- add a test, do not
   change behavior, just verify your environment is right.

---

## The OpenAPI contract (the interface-collaboration artifact)

FastAPI generates an OpenAPI 3 document at `/openapi.json` and a
Swagger UI at `/docs`. That document is the **interface contract** between
the imaginary frontend developer working on the React UI (deferred to
M7) and the backend developer working on this service. Both can work
against the same schema without sharing a codebase, without coordinating
on a wire format, and without manual API documentation that drifts from
reality.

This is one of the three Outcome 1 artifacts the narrative claims:

1. **Personas above** -- named human users with concrete decisions, not
   abstract "user roles."
2. **OpenAPI** -- machine-readable contract that lets two developers
   work in parallel against the same boundary.
3. **This file** -- branching, PR template, onboarding. The hygiene a
   second engineer would need to actually join.
