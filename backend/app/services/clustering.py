# File: backend/app/services/clustering.py
"""
Fraud clustering + risk scoring (pure algorithms).

WHY: Two cases belong to the same fraud cluster if they share at least
one entity (a UPI, phone, account...). This is transitive: A-B (shared
UPI) and B-C (shared phone) put A, B, C in one cluster. That is a graph
connected-components problem, solved here with union-find (disjoint set).

This module is DELIBERATELY pure: it takes plain data structures and
returns plain results, with no database access. That keeps the
investigative logic deterministic, auditable, and unit-testable without a
DB -- the same discipline used for extraction/normalization.

Risk scoring is rule-based and explainable: the score is a transparent
sum of observable factors, never a black box. An investigator must be
able to see WHY a cluster is rated critical.
"""
from dataclasses import dataclass, field

from app.models.enums import EntityType, RiskLevel


class _UnionFind:
    """Disjoint-set structure for connected-components clustering."""

    def __init__(self) -> None:
        self._parent: dict[int, int] = {}

    def add(self, item: int) -> None:
        self._parent.setdefault(item, item)

    def find(self, item: int) -> int:
        # Path compression keeps the structure near-flat.
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[item] != root:
            self._parent[item], item = root, self._parent[item]
        return root

    def union(self, a: int, b: int) -> None:
        self._parent[self.find(a)] = self.find(b)


@dataclass
class ClusterInput:
    """
    Minimal input for clustering.

    entity_to_cases: for each entity id, the set of case ids it appears in.
    An entity present in 2+ cases is what links those cases together.
    """
    entity_to_cases: dict[int, set[int]]


@dataclass
class Cluster:
    cluster_id: int
    case_ids: set[int] = field(default_factory=set)
    # Entities that link the cluster's cases (appear in 2+ of its cases).
    linking_entity_ids: set[int] = field(default_factory=set)


def build_clusters(data: ClusterInput) -> list[Cluster]:
    """Group cases into clusters by shared entities (connected components)."""
    uf = _UnionFind()

    # Register every case so even singletons appear.
    for cases in data.entity_to_cases.values():
        for case_id in cases:
            uf.add(case_id)

    # Union cases that share an entity.
    for cases in data.entity_to_cases.values():
        case_list = sorted(cases)
        for other in case_list[1:]:
            uf.union(case_list[0], other)

    # Gather components.
    components: dict[int, set[int]] = {}
    for case_id in list(uf._parent.keys()):
        root = uf.find(case_id)
        components.setdefault(root, set()).add(case_id)

    # Attach the entities that actually link each cluster's cases.
    clusters: list[Cluster] = []
    for idx, (_root, case_ids) in enumerate(
        sorted(components.items(), key=lambda kv: (-len(kv[1]), min(kv[1]))), start=1
    ):
        linking = {
            eid
            for eid, cases in data.entity_to_cases.items()
            if len(cases & case_ids) >= 2
        }
        clusters.append(
            Cluster(cluster_id=idx, case_ids=set(case_ids), linking_entity_ids=linking)
        )
    return clusters


# --- Risk scoring ---------------------------------------------------------

# Weights make FINANCIAL links count more than weak signals (e.g. a shared
# generic domain). This is the 'why' behind a score, kept explicit.
_ENTITY_TYPE_WEIGHT: dict[EntityType, float] = {
    EntityType.UPI: 3.0,
    EntityType.BANK_ACCOUNT: 3.0,
    EntityType.CRYPTO_WALLET: 3.0,
    EntityType.UTR: 2.5,
    EntityType.IFSC: 1.5,
    EntityType.PHONE: 2.0,
    EntityType.EMAIL: 1.5,
    EntityType.TELEGRAM: 1.5,
    EntityType.IP_ADDRESS: 1.0,
    EntityType.DOMAIN: 1.0,
    EntityType.URL: 1.0,
}


@dataclass
class RiskBreakdown:
    """Transparent, explainable risk result."""
    score: float
    level: RiskLevel
    factors: dict[str, float] = field(default_factory=dict)


def score_cluster(
    *,
    case_count: int,
    linking_entity_types: list[EntityType],
    total_mentions: int,
) -> RiskBreakdown:
    """
    Compute an explainable risk score for a cluster.

    Factors (each surfaced in the breakdown so the score is auditable):
      - case_count: more linked cases => broader fraud network.
      - entity_weight: financial links weigh more than weak signals.
      - mention_volume: repeated mentions indicate stronger evidence.
    """
    case_factor = float(case_count) * 2.0
    entity_factor = sum(_ENTITY_TYPE_WEIGHT.get(t, 1.0) for t in linking_entity_types)
    mention_factor = float(total_mentions) * 0.25

    score = round(case_factor + entity_factor + mention_factor, 2)

    if score >= 30:
        level = RiskLevel.CRITICAL
    elif score >= 15:
        level = RiskLevel.HIGH
    elif score >= 6:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    return RiskBreakdown(
        score=score,
        level=level,
        factors={
            "case_count": round(case_factor, 2),
            "entity_weight": round(entity_factor, 2),
            "mention_volume": round(mention_factor, 2),
        },
    )
