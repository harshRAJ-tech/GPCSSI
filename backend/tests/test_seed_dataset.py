# File: backend/tests/test_seed_dataset.py
"""
Database-layer tests for the synthetic dataset + clustering + correlation.

WHY: The pure algorithms (extraction, normalization, clustering) already
have unit tests, but the DB-touching code -- entity_service, cluster_service
and correlation -- did not. This module closes that gap with an in-memory
SQLite database, and at the same time VERIFIES the synthetic dataset is
correctly designed.

The key guarantee under test: when the synthetic narratives are ingested
through the REAL pipeline (extract -> normalize -> occurrence), the
clustering engine discovers exactly the four designed fraud networks
(sizes 8, 6, 5, 4) and the five noise cases stay out of every cluster.
If a narrative ever accidentally shares an extracted entity across
clusters (e.g. an amount that matches the bank-account pattern), this
test fails loudly and points at a dataset bug -- not a silent merge.

DESIGN NOTE -- isolated engine:
The application binds a global engine to settings.DATABASE_URL (Postgres)
at import time. We do NOT use that engine here. Instead we build a fresh
in-memory SQLite engine, create the schema on it from the shared
Base.metadata, and run every query against a session bound to it. This
keeps the test hermetic: no Postgres, no .env, no network.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Importing the models package registers every table on Base.metadata.
import app.models  # noqa: F401
from app.core.database import Base
from app.models.enums import EntityType, UserRole
from app.models.user import User
from app.services import cluster_service, correlation
from app.services.user_service import create_user

from scripts import seed_synthetic

# Expected cluster sizes for the four designed fraud networks.
_EXPECTED_CLUSTER_SIZES = sorted([8, 6, 5, 4], reverse=True)

# Titles of the standalone noise cases (without the synthetic prefix).
_NOISE_TITLES = {title for title, _ in seed_synthetic._noise_cases()}


@pytest.fixture()
def db() -> Session:
    """
    Provide a session bound to a throwaway in-memory SQLite database.

    StaticPool + a single shared connection keep the in-memory schema
    alive for the whole test (a normal pool would discard it). The schema
    is built directly from the ORM models, so it always matches them.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seeded_db(db: Session) -> Session:
    """A DB seeded with an admin and the full synthetic dataset."""
    create_user(
        db,
        username="seed_admin",
        full_name="Seed Admin",
        password="test-password-123",
        role=UserRole.SYSTEM_ADMIN,
    )
    db.commit()

    exit_code = seed_synthetic.seed(db, reset=False)
    assert exit_code == 0
    return db


def test_seed_requires_admin(db: Session) -> None:
    """With no SYSTEM_ADMIN present, seeding fails closed (exit code 2)."""
    assert seed_synthetic.seed(db, reset=False) == 2


def test_seed_creates_all_cases(seeded_db: Session) -> None:
    """All 28 synthetic cases are persisted."""
    cases = seed_synthetic._existing_synthetic(seeded_db)
    assert len(cases) == len(seed_synthetic._all_cases()) == 28


def test_seed_is_idempotent(seeded_db: Session) -> None:
    """Re-running without --reset is a no-op and does not duplicate cases."""
    before = len(seed_synthetic._existing_synthetic(seeded_db))
    assert seed_synthetic.seed(seeded_db, reset=False) == 0
    after = len(seed_synthetic._existing_synthetic(seeded_db))
    assert before == after == 28


def test_clustering_discovers_exactly_four_networks(seeded_db: Session) -> None:
    """
    The clustering engine, fed by REAL extraction, finds exactly the four
    designed fraud networks with the expected case counts.
    """
    clusters = cluster_service.compute_clusters(seeded_db, min_cases=2)
    sizes = sorted((c.case_count for c in clusters), reverse=True)
    assert sizes == _EXPECTED_CLUSTER_SIZES, (
        f"expected cluster sizes {_EXPECTED_CLUSTER_SIZES}, got {sizes}. "
        "A mismatch usually means a narrative accidentally shares an "
        "extracted entity across clusters (e.g. an amount matching the "
        "bank-account pattern)."
    )


def test_noise_cases_are_not_clustered(seeded_db: Session) -> None:
    """None of the standalone noise cases appear in any discovered cluster."""
    clusters = cluster_service.compute_clusters(seeded_db, min_cases=2)
    clustered_case_ids: set[int] = set()
    for c in clusters:
        clustered_case_ids.update(c.case_ids)

    prefix = seed_synthetic.SYNTHETIC_TITLE_PREFIX
    noise_ids = {
        case.id
        for case in seed_synthetic._existing_synthetic(seeded_db)
        if case.title.removeprefix(prefix) in _NOISE_TITLES
    }
    assert noise_ids, "expected to find seeded noise cases"
    assert clustered_case_ids.isdisjoint(noise_ids), (
        "a noise case leaked into a cluster -- the engine failed to "
        "discriminate, or a noise narrative shares an entity with a cluster."
    )


def test_highest_risk_cluster_is_ranked_first(seeded_db: Session) -> None:
    """compute_clusters returns clusters in descending risk order."""
    clusters = cluster_service.compute_clusters(seeded_db, min_cases=2)
    scores = [c.risk.score for c in clusters]
    assert scores == sorted(scores, reverse=True)
    # The 8-case KYC/UPI ring is the broadest network; it should top the list.
    assert clusters[0].case_count == 8


def test_correlation_links_shared_upi_across_cases(seeded_db: Session) -> None:
    """
    Searching the shared UPI resolves to one entity linked to the cases
    that DIRECTLY contain it, and surfaces connected entities.

    NOTE the direct-vs-transitive distinction this test pins down:
    the UPI `kycupdate@ybl` appears verbatim in only 5 of Cluster A's 8
    cases (1, 2, 3, 6, 7). The other 3 cases (4, 5, 8) join the *cluster*
    transitively, via the shared phone and collection account -- a
    relationship discovered by clustering (union-find), not by a direct
    occurrence lookup. So correlation correctly reports 5 here; the full
    8-case network is asserted separately in the clustering test. Those
    connecting entities must still show up in `connected_entities`.
    """
    result = correlation.correlate(seeded_db, value=seed_synthetic._A_UPI)
    assert result is not None
    assert result.entity_type == EntityType.UPI
    # 5 cases contain the UPI directly (not the full 8-case cluster).
    assert len(result.cases) == 5

    # The transitive links (shared phone + account) must surface as
    # connected entities -- that is what lets an investigator pivot from
    # the UPI to the wider network.
    connected_types = {c.entity_type for c in result.connected_entities}
    assert EntityType.PHONE in connected_types
    assert EntityType.BANK_ACCOUNT in connected_types


def test_correlation_unknown_value_returns_none(seeded_db: Session) -> None:
    """A value that was never ingested correlates to nothing."""
    assert correlation.correlate(seeded_db, value="neverseen@xyz") is None
