# CIIP Domain Model

This document defines the core objects of the Cyber Investigation
Intelligence Platform (CIIP) prototype and the reasoning behind the
schema. All data is **synthetic** (see `SECURITY.md`).

## Entity-relationship overview

```text
User 1---* Case 1---* Evidence
User 1---* AuditLog
Entity *---* Entity   (via Relationship)
```

## Tables

### users
Officers and analysts who authenticate to the system.
- `hashed_password`: bcrypt hash only; plaintext is never stored.
- `role`: drives role-based access control (RBAC).
- `is_active`: accounts are **disabled, never deleted**, so audit history
  is preserved.

### cases
The top-level investigation container. Everything traces back to a case.
- `created_by` uses `ON DELETE RESTRICT`: you cannot delete a user who
  still owns cases, protecting traceability.

### evidence
Every uploaded file, treated as immutable evidence.
- `sha256`: integrity anchor for chain-of-custody. A recomputed hash that
  no longer matches proves tampering.
- `original_filename` vs `stored_path`: the user-supplied name is
  **display only**. The server generates the on-disk path, so a malicious
  filename can never cause path traversal.

### entities
Investigative artifacts (UPI, phone, account, wallet, etc.).
- **Key rule:** unique on `(entity_type, normalized_value)`. The same UPI
  across 10 complaints is **one** entity row. This is what makes
  correlation a precise lookup rather than fuzzy text matching.
- `raw_value` is kept alongside `normalized_value` so investigators can
  still see the original form.

### relationships
Edges between entities (`USES`, `OWNS`, `TRANSFERRED_TO`, ...).
- `confidence` (0.0-1.0) distinguishes a **directly observed** link from
  an **inferred** one. Investigators must know fact from hint.
- Mirrors what Neo4j will hold; PostgreSQL remains the source of truth.

### audit_logs
Who did what, when. Treated as **MVP, not V2**.
- Append-only at the application layer (insert only).
- **Known limitation (follow-up):** true immutability needs DB-level
  enforcement (INSERT-only role + trigger blocking UPDATE/DELETE).
- Stores only action + actor + target reference + source IP. **No request
  bodies or PII**, so the audit log never becomes a leak vector.

## Design decisions confirmed
1. Entity uniqueness on `(entity_type, normalized_value)`.
2. Audit log append-only at app layer now; DB-level hardening tracked as a
   follow-up.
3. Schema created via `Base.metadata.create_all` for the prototype;
   Alembic migrations to be introduced once the schema stabilizes.
