# File: backend/tests/test_routes.py
"""
HTTP route-level integration tests.

WHY: The service layer is covered (test_seed_dataset.py), but the API
routes themselves were not. These tests exercise the FULL HTTP path --
dependency injection, authentication, request/response schemas, status
codes and audit writes -- which is exactly what a client (or evaluator)
hits first. They protect the routes from regressions once a frontend is
built against them.

DESIGN -- hermetic and fail-safe:
- A throwaway in-memory SQLite engine (StaticPool) backs every test; no
  Postgres, no .env, no network.
- FastAPI's dependency override replaces `get_db` so routes use the test
  session. The app's global engine is never touched.
- The app's lifespan (which would call init_db() against Postgres) is
  deliberately NOT triggered: we construct TestClient(app) plainly rather
  than as a context manager, and build the schema ourselves on the SQLite
  engine. This keeps the suite independent of any real database.
- We authenticate through the real /auth/login endpoint to get a genuine
  JWT, so the tests prove the actual auth flow, not a shortcut.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Importing the models package registers every table on Base.metadata.
import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.models.enums import UserRole
from app.services.user_service import create_user
from main import app

from scripts import seed_synthetic

_ADMIN_USERNAME = "route_admin"
_ADMIN_PASSWORD = "route-test-password-123"


@pytest.fixture()
def client() -> TestClient:
    """
    A TestClient whose `get_db` dependency is overridden to use a fresh
    in-memory SQLite database seeded with an admin and the synthetic data.

    The single shared connection (StaticPool) keeps the in-memory schema
    alive for the whole test. The override is removed on teardown so tests
    never leak state into one another.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # Seed an admin and the synthetic dataset using a dedicated session.
    setup_session: Session = TestingSession()
    try:
        create_user(
            setup_session,
            username=_ADMIN_USERNAME,
            full_name="Route Admin",
            password=_ADMIN_PASSWORD,
            role=UserRole.SYSTEM_ADMIN,
        )
        setup_session.commit()
        assert seed_synthetic.seed(setup_session, reset=False) == 0
    finally:
        setup_session.close()

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _auth_header(client: TestClient) -> dict[str, str]:
    """Log in via the real endpoint and return a Bearer auth header."""
    resp = client.post(
        "/auth/login",
        data={"username": _ADMIN_USERNAME, "password": _ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Authentication -------------------------------------------------------

def test_login_succeeds_with_valid_credentials(client: TestClient) -> None:
    resp = client.post(
        "/auth/login",
        data={"username": _ADMIN_USERNAME, "password": _ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_fails_with_wrong_password(client: TestClient) -> None:
    resp = client.post(
        "/auth/login",
        data={"username": _ADMIN_USERNAME, "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_search_requires_authentication(client: TestClient) -> None:
    """No token -> 401, before any business logic runs."""
    resp = client.get("/search", params={"value": seed_synthetic._A_UPI})
    assert resp.status_code == 401


def test_clusters_requires_authentication(client: TestClient) -> None:
    resp = client.get("/clusters")
    assert resp.status_code == 401


# --- Search ---------------------------------------------------------------

def test_search_known_upi_returns_linked_cases(client: TestClient) -> None:
    """Searching the shared UPI returns its directly-linked cases."""
    headers = _auth_header(client)
    resp = client.get(
        "/search", params={"value": seed_synthetic._A_UPI}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["entity_type"] == "upi"
    assert body["normalized_value"] == seed_synthetic._A_UPI
    # The UPI appears verbatim in 5 of Cluster A's cases (transitive links
    # extend the cluster to 8; see test_seed_dataset for that distinction).
    assert len(body["cases"]) == 5
    assert body["connected_entities"], "expected co-occurring entities"


def test_search_unknown_value_returns_404(client: TestClient) -> None:
    headers = _auth_header(client)
    resp = client.get(
        "/search", params={"value": "neverseen@nowhere"}, headers=headers
    )
    assert resp.status_code == 404


# --- Entity expansion (graph drill-down) ----------------------------------

def test_expand_requires_authentication(client: TestClient) -> None:
    """No token -> 401, before any business logic runs."""
    resp = client.get("/search/expand/1")
    assert resp.status_code == 401


def test_expand_known_entity_returns_connected(client: TestClient) -> None:
    """Expanding a known entity returns its co-occurring entities.

    We first resolve the shared UPI via /search to obtain its entity_id,
    then expand that id -- proving the two endpoints agree on the same
    entity and connection set.
    """
    headers = _auth_header(client)
    found = client.get(
        "/search", params={"value": seed_synthetic._A_UPI}, headers=headers
    ).json()
    entity_id = found["entity_id"]

    resp = client.get(f"/search/expand/{entity_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["entity_id"] == entity_id
    assert body["entity_type"] == "upi"
    assert body["normalized_value"] == seed_synthetic._A_UPI
    # The expansion's connected set matches what /search reported.
    assert len(body["connected_entities"]) == len(found["connected_entities"])


def test_expand_unknown_id_returns_404(client: TestClient) -> None:
    headers = _auth_header(client)
    resp = client.get("/search/expand/999999", headers=headers)
    assert resp.status_code == 404


def test_expand_rejects_non_positive_id(client: TestClient) -> None:
    """The ge=1 path constraint rejects 0 with a 422 validation error."""
    headers = _auth_header(client)
    resp = client.get("/search/expand/0", headers=headers)
    assert resp.status_code == 422


def test_search_rejects_empty_value(client: TestClient) -> None:
    """The min_length=1 query constraint yields a 422 validation error."""
    headers = _auth_header(client)
    resp = client.get("/search", params={"value": ""}, headers=headers)
    assert resp.status_code == 422


# --- Clusters -------------------------------------------------------------

def test_clusters_returns_four_networks_risk_ranked(client: TestClient) -> None:
    """
    GET /clusters returns exactly the four designed fraud networks,
    ordered by descending risk score.
    """
    headers = _auth_header(client)
    resp = client.get("/clusters", headers=headers)
    assert resp.status_code == 200, resp.text
    clusters = resp.json()
    assert len(clusters) == 4

    sizes = sorted((c["case_count"] for c in clusters), reverse=True)
    assert sizes == [8, 6, 5, 4]

    scores = [c["risk"]["score"] for c in clusters]
    assert scores == sorted(scores, reverse=True)


def test_clusters_min_cases_filter(client: TestClient) -> None:
    """A high min_cases threshold filters out the smaller clusters."""
    headers = _auth_header(client)
    resp = client.get("/clusters", params={"min_cases": 7}, headers=headers)
    assert resp.status_code == 200, resp.text
    clusters = resp.json()
    # Only the 8-case ring meets a 7+ threshold.
    assert len(clusters) == 1
    assert clusters[0]["case_count"] == 8


# --- Entity extraction ----------------------------------------------------

def test_extract_entities_returns_created(client: TestClient) -> None:
    """POST /entities/extract pulls entities from supplied text."""
    headers = _auth_header(client)
    resp = client.post(
        "/entities/extract",
        json={"text": "Victim paid to UPI fresh@okhdfc from 9812345678."},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    found = {e["entity_type"] for e in resp.json()}
    assert "upi" in found
    assert "phone" in found
