from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.case import Case
from app.models.evidence import Evidence
from app.models.entity import Entity

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Fetch aggregated statistics for the intelligence dashboard."""
    # 1. Total counts
    total_cases = db.query(func.count(Case.id)).scalar() or 0
    total_evidence = db.query(func.count(Evidence.id)).scalar() or 0
    total_entities = db.query(func.count(Entity.id)).scalar() or 0

    # 2. Entity Breakdown by Type
    entity_counts = db.query(Entity.entity_type, func.count(Entity.id)).group_by(Entity.entity_type).all()
    entity_breakdown = [{"name": etype.value.upper(), "value": count} for etype, count in entity_counts]

    # 3. Cases Over Time (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    cases_recent = db.query(Case.created_at).filter(Case.created_at >= thirty_days_ago).all()
    
    time_series = {}
    for i in range(30):
        day = (thirty_days_ago + timedelta(days=i)).strftime("%Y-%m-%d")
        time_series[day] = 0
        
    for (created_at,) in cases_recent:
        day_str = created_at.strftime("%Y-%m-%d")
        if day_str in time_series:
            time_series[day_str] += 1
            
    trend_data = [{"date": k, "cases": v} for k, v in time_series.items()]

    # 4. Recent Cases
    recent_cases = db.query(Case).order_by(Case.created_at.desc()).limit(5).all()
    recent_cases_list = [
        {
            "id": c.id,
            "title": c.title,
            "risk_level": c.risk_level.value if c.risk_level else "low",
            "created_at": c.created_at.isoformat()
        } for c in recent_cases
    ]

    return {
        "overview": {
            "total_cases": total_cases,
            "total_evidence": total_evidence,
            "total_entities": total_entities,
        },
        "entity_breakdown": entity_breakdown,
        "trend": trend_data,
        "recent_cases": recent_cases_list
    }
