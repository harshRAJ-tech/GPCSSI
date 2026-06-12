# File: backend/app/services/cluster_service.py
"""
Cluster service: bridges the database to the pure clustering algorithm.

WHY: Keep all DB access here, and the algorithm pure in clustering.py.
This loads entity->case occurrences, runs union-find, scores each cluster
from observable data, and returns enriched results for the API.

Clusters are computed ON DEMAND (not persisted) for the prototype: the
result is always consistent with current data and avoids stale snapshots.
"""
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.entity_occurrence import EntityOccurrence
from app.models.enums import EntityType
from app.services import clustering
from app.services.clustering import Cluster, ClusterInput, RiskBreakdown


@dataclass
class ScoredCluster:
    cluster_id: int
    case_ids: list[int]
    case_count: int
    linking_entity_ids: list[int]
    risk: RiskBreakdown


def _load_entity_to_cases(db: Session) -> dict[int, set[int]]:
    """Map each entity id to the set of case ids it occurs in."""
    rows = db.execute(
        select(EntityOccurrence.entity_id, EntityOccurrence.case_id)
    ).all()
    mapping: dict[int, set[int]] = {}
    for entity_id, case_id in rows:
        mapping.setdefault(entity_id, set()).add(case_id)
    return mapping


def _entity_types(db: Session, entity_ids: set[int]) -> dict[int, EntityType]:
    if not entity_ids:
        return {}
    rows = db.execute(
        select(Entity.id, Entity.entity_type).where(Entity.id.in_(entity_ids))
    ).all()
    return {eid: etype for eid, etype in rows}


def _total_mentions(db: Session, case_ids: set[int]) -> int:
    if not case_ids:
        return 0
    total = db.scalar(
        select(func.coalesce(func.sum(EntityOccurrence.mention_count), 0)).where(
            EntityOccurrence.case_id.in_(case_ids)
        )
    )
    return int(total or 0)


def compute_clusters(db: Session, *, min_cases: int = 2) -> list[ScoredCluster]:
    """Build, score and return fraud clusters with at least `min_cases`."""
    entity_to_cases = _load_entity_to_cases(db)
    clusters: list[Cluster] = clustering.build_clusters(
        ClusterInput(entity_to_cases=entity_to_cases)
    )

    scored: list[ScoredCluster] = []
    for cluster in clusters:
        if len(cluster.case_ids) < min_cases:
            continue

        type_map = _entity_types(db, cluster.linking_entity_ids)
        linking_types = [type_map[e] for e in cluster.linking_entity_ids if e in type_map]
        mentions = _total_mentions(db, cluster.case_ids)

        risk = clustering.score_cluster(
            case_count=len(cluster.case_ids),
            linking_entity_types=linking_types,
            total_mentions=mentions,
        )
        scored.append(
            ScoredCluster(
                cluster_id=cluster.cluster_id,
                case_ids=sorted(cluster.case_ids),
                case_count=len(cluster.case_ids),
                linking_entity_ids=sorted(cluster.linking_entity_ids),
                risk=risk,
            )
        )

    # Highest risk first -- the investigator's priority order.
    scored.sort(key=lambda c: c.risk.score, reverse=True)
    return scored
