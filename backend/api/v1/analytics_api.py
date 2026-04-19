"""
Analytics API — Video performance tracking and reporting.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.analytics import VideoAnalytics
from backend.models.content_job import ContentJob

logger = logging.getLogger("api.analytics")

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", summary="Get analytics overview")
def get_overview(
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Aggregate analytics across all published videos"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Aggregate metrics
    stats = db.query(
        func.count(VideoAnalytics.id).label("total_videos"),
        func.sum(VideoAnalytics.views).label("total_views"),
        func.sum(VideoAnalytics.likes).label("total_likes"),
        func.sum(VideoAnalytics.comments).label("total_comments"),
        func.sum(VideoAnalytics.shares).label("total_shares"),
        func.avg(VideoAnalytics.engagement_rate).label("avg_engagement"),
    ).filter(
        VideoAnalytics.created_at >= cutoff
    ).first()

    # Per-platform breakdown
    platform_stats = db.query(
        VideoAnalytics.platform,
        func.count(VideoAnalytics.id).label("count"),
        func.sum(VideoAnalytics.views).label("views"),
        func.sum(VideoAnalytics.likes).label("likes"),
        func.avg(VideoAnalytics.engagement_rate).label("avg_engagement"),
    ).filter(
        VideoAnalytics.created_at >= cutoff
    ).group_by(VideoAnalytics.platform).all()

    # Recent jobs count
    recent_jobs = db.query(func.count(ContentJob.id)).filter(
        ContentJob.created_at >= cutoff,
        ContentJob.status == "completed",
    ).scalar()

    return {
        "period_days": days,
        "total_videos": stats.total_videos or 0,
        "total_views": stats.total_views or 0,
        "total_likes": stats.total_likes or 0,
        "total_comments": stats.total_comments or 0,
        "total_shares": stats.total_shares or 0,
        "avg_engagement_rate": round(stats.avg_engagement or 0, 2),
        "completed_jobs": recent_jobs or 0,
        "platforms": [
            {
                "platform": p.platform,
                "video_count": p.count,
                "total_views": p.views or 0,
                "total_likes": p.likes or 0,
                "avg_engagement": round(p.avg_engagement or 0, 2),
            }
            for p in platform_stats
        ],
    }


@router.get("/jobs/{job_id}", summary="Get analytics for a specific job")
def get_job_analytics(job_id: str, db: Session = Depends(get_db)):
    """Get per-video metrics for a job"""
    analytics = db.query(VideoAnalytics).filter(
        VideoAnalytics.job_id == job_id
    ).all()

    if not analytics:
        return {"job_id": job_id, "videos": [], "message": "No analytics data yet"}

    return {
        "job_id": job_id,
        "videos": [a.to_dict() for a in analytics],
        "total_views": sum(a.views or 0 for a in analytics),
        "total_likes": sum(a.likes or 0 for a in analytics),
    }


@router.get("/trends", summary="Get performance trends over time")
def get_trends(
    days: int = 30,
    platform: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get daily aggregated metrics for charting"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(VideoAnalytics).filter(VideoAnalytics.created_at >= cutoff)
    if platform:
        query = query.filter(VideoAnalytics.platform == platform)

    records = query.order_by(VideoAnalytics.created_at.asc()).all()

    # Group by date
    daily = {}
    for r in records:
        date_key = r.created_at.strftime("%Y-%m-%d") if r.created_at else "unknown"
        if date_key not in daily:
            daily[date_key] = {"date": date_key, "views": 0, "likes": 0, "videos": 0}
        daily[date_key]["views"] += r.views or 0
        daily[date_key]["likes"] += r.likes or 0
        daily[date_key]["videos"] += 1

    return {
        "period_days": days,
        "platform": platform or "all",
        "data": list(daily.values()),
    }


@router.get("/top-videos", summary="Get top performing videos")
def get_top_videos(
    limit: int = 10,
    sort_by: str = "views",
    db: Session = Depends(get_db),
):
    """Get top performing videos sorted by metric"""
    sort_column = getattr(VideoAnalytics, sort_by, VideoAnalytics.views)

    top = db.query(VideoAnalytics).order_by(
        sort_column.desc()
    ).limit(limit).all()

    return {
        "sort_by": sort_by,
        "videos": [a.to_dict() for a in top],
    }


@router.get("/ab-results", summary="Get A/B test results")
def get_ab_results(db: Session = Depends(get_db)):
    """Compare A/B test variant performance"""
    # Get videos with variant labels
    variants = db.query(VideoAnalytics).filter(
        VideoAnalytics.variant != "",
        VideoAnalytics.variant.isnot(None),
    ).all()

    if not variants:
        return {"message": "No A/B test data yet", "results": []}

    # Group by variant
    by_variant = {}
    for v in variants:
        label = v.variant
        if label not in by_variant:
            by_variant[label] = {
                "variant": label,
                "video_count": 0,
                "total_views": 0,
                "total_likes": 0,
                "avg_engagement": 0,
                "engagement_rates": [],
            }
        by_variant[label]["video_count"] += 1
        by_variant[label]["total_views"] += v.views or 0
        by_variant[label]["total_likes"] += v.likes or 0
        if v.engagement_rate:
            by_variant[label]["engagement_rates"].append(v.engagement_rate)

    # Calculate averages
    results = []
    for label, data in by_variant.items():
        rates = data.pop("engagement_rates", [])
        data["avg_engagement"] = round(sum(rates) / len(rates), 2) if rates else 0
        results.append(data)

    # Sort by engagement
    results.sort(key=lambda x: x["avg_engagement"], reverse=True)

    return {"results": results}
