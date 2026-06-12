# File: backend/tests/test_clustering.py
"""
Unit tests for the pure clustering + risk scoring algorithms.

WHY: Clustering decides which cases form a fraud network -- a high-impact
investigative claim. These tests lock down connected-components behaviour
(including transitive links) and the explainable risk ordering, with no
database required.
"""
from app.models.enums import EntityType, RiskLevel
from app.services.clustering import (
    ClusterInput,
    build_clusters,
    score_cluster,
)


def _cluster_of(clusters, case_id):
    return next(c for c in clusters if case_id in c.case_ids)


def test_shared_entity_links_two_cases() -> None:
    # Entity 1 appears in cases 10 and 20 -> they cluster together.
    data = ClusterInput(entity_to_cases={1: {10, 20}})
    clusters = build_clusters(data)
    assert len(clusters) == 1
    assert clusters[0].case_ids == {10, 20}
    assert 1 in clusters[0].linking_entity_ids


def test_transitive_linking() -> None:
    # 10-20 via entity 1, 20-30 via entity 2 -> {10,20,30} is one cluster.
    data = ClusterInput(entity_to_cases={1: {10, 20}, 2: {20, 30}})
    clusters = build_clusters(data)
    assert _cluster_of(clusters, 10).case_ids == {10, 20, 30}


def test_unrelated_cases_form_separate_clusters() -> None:
    data = ClusterInput(entity_to_cases={1: {10, 11}, 2: {20, 21}})
    clusters = build_clusters(data)
    assert len(clusters) == 2
    assert _cluster_of(clusters, 10).case_ids == {10, 11}
    assert _cluster_of(clusters, 20).case_ids == {20, 21}


def test_single_case_entity_does_not_link() -> None:
    # Entity only in one case -> that case is its own (singleton) cluster.
    data = ClusterInput(entity_to_cases={1: {10}, 2: {10, 20}})
    clusters = build_clusters(data)
    # entity 2 links 10-20; entity 1 (only case 10) is not a linking entity
    # of a 2+ membership on its own.
    c = _cluster_of(clusters, 10)
    assert c.case_ids == {10, 20}
    assert 2 in c.linking_entity_ids


def test_risk_financial_links_score_higher() -> None:
    weak = score_cluster(
        case_count=2, linking_entity_types=[EntityType.DOMAIN], total_mentions=2
    )
    strong = score_cluster(
        case_count=2, linking_entity_types=[EntityType.UPI], total_mentions=2
    )
    assert strong.score > weak.score


def test_risk_levels_escalate_with_size() -> None:
    small = score_cluster(
        case_count=2, linking_entity_types=[EntityType.EMAIL], total_mentions=1
    )
    big = score_cluster(
        case_count=12,
        linking_entity_types=[EntityType.UPI, EntityType.BANK_ACCOUNT],
        total_mentions=40,
    )
    assert big.score > small.score
    assert big.level == RiskLevel.CRITICAL


def test_risk_breakdown_is_transparent() -> None:
    result = score_cluster(
        case_count=3, linking_entity_types=[EntityType.UPI], total_mentions=4
    )
    # Every contributing factor must be surfaced for auditability.
    assert set(result.factors) == {"case_count", "entity_weight", "mention_volume"}
    assert abs(sum(result.factors.values()) - result.score) < 0.01
