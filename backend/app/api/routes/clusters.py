# File: backend/app/api/routes/clusters.py
"""
Fraud cluster routes.

WHY: Surfaces the 'Cluster #N: X cases, risk CRITICAL' view -- the
highest-value investigative output. Clusters are computed on demand from
current data, authenticated, and audited. Results are ordered highest
risk first so the investigator sees priorities immediately.
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.cluster import ClusterOut
from app.services import audit, cluster_service

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("", response_model=list[ClusterOut])
def list_clusters(
    request: Request,
    min_cases: int = Query(default=2, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """Return fraud clusters (cases linked by shared entities), risk-ranked."""
    clusters = cluster_service.compute_clusters(db, min_cases=min_cases)

    audit.record(
        db,
        action=AuditAction.SEARCH,
        user_id=current_user.id,
        target_ref=f"clusters:{len(clusters)}",
        source_ip=request.client.host if request.client else None,
    )
    db.commit()
    return clusters
