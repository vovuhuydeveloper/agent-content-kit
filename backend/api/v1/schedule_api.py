"""
Schedule API — CRUD endpoints for content schedules (content calendar).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.base import generate_uuid
from backend.models.schedule import ContentSchedule

logger = logging.getLogger("api.schedule")

router = APIRouter(prefix="/schedules", tags=["Content Calendar"])


class ScheduleCreate(BaseModel):
    name: str
    cron_expression: str = "0 9 * * 1"  # Default: Monday 9am
    timezone: str = "Asia/Ho_Chi_Minh"
    source_url: str
    source_type: str = "web"
    language: str = "vi"
    niche: str = ""
    video_count: int = 3
    platforms: list = ["tiktok", "youtube"]
    competitor_urls: list = []
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    source_url: Optional[str] = None
    language: Optional[str] = None
    niche: Optional[str] = None
    video_count: Optional[int] = None
    platforms: Optional[list] = None
    enabled: Optional[bool] = None


@router.get("/", summary="List all schedules")
def list_schedules(db: Session = Depends(get_db)):
    """List all content schedules"""
    schedules = db.query(ContentSchedule).order_by(
        ContentSchedule.created_at.desc()
    ).all()

    return {
        "total": len(schedules),
        "schedules": [s.to_dict() for s in schedules],
    }


@router.post("/", summary="Create a schedule")
def create_schedule(data: ScheduleCreate, db: Session = Depends(get_db)):
    """Create a new scheduled content job"""
    schedule = ContentSchedule(
        id=generate_uuid(),
        name=data.name,
        cron_expression=data.cron_expression,
        timezone=data.timezone,
        source_url=data.source_url,
        source_type=data.source_type,
        language=data.language,
        niche=data.niche,
        video_count=data.video_count,
        platforms=data.platforms,
        competitor_urls=data.competitor_urls,
        enabled=data.enabled,
    )

    # Calculate next run time
    try:
        from backend.tasks.schedule_tasks import calculate_next_run
        schedule.next_run_at = calculate_next_run(data.cron_expression, data.timezone)
    except Exception:
        pass

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    logger.info(f"Schedule '{data.name}' created: {schedule.id}")

    return {"schedule": schedule.to_dict(), "message": "Schedule created!"}


@router.get("/{schedule_id}", summary="Get schedule details")
def get_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """Get a specific schedule"""
    schedule = db.query(ContentSchedule).filter(
        ContentSchedule.id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(404, "Schedule not found")
    return schedule.to_dict()


@router.put("/{schedule_id}", summary="Update a schedule")
def update_schedule(schedule_id: str, data: ScheduleUpdate, db: Session = Depends(get_db)):
    """Update a schedule"""
    schedule = db.query(ContentSchedule).filter(
        ContentSchedule.id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(schedule, field, value)

    # Recalculate next run if cron changed
    if data.cron_expression:
        try:
            from backend.tasks.schedule_tasks import calculate_next_run
            tz = data.timezone or schedule.timezone
            schedule.next_run_at = calculate_next_run(data.cron_expression, tz)
        except Exception:
            pass

    db.commit()
    db.refresh(schedule)

    return {"schedule": schedule.to_dict(), "message": "Schedule updated!"}


@router.delete("/{schedule_id}", summary="Delete a schedule")
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """Delete a schedule"""
    schedule = db.query(ContentSchedule).filter(
        ContentSchedule.id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    db.delete(schedule)
    db.commit()
    return {"message": f"Schedule '{schedule.name}' deleted"}


@router.post("/{schedule_id}/run-now", summary="Trigger schedule immediately")
def run_schedule_now(schedule_id: str, db: Session = Depends(get_db)):
    """Manually trigger a scheduled job"""
    schedule = db.query(ContentSchedule).filter(
        ContentSchedule.id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    from backend.tasks.schedule_tasks import run_scheduled_job
    run_scheduled_job.delay(schedule_id)

    return {"message": f"Schedule '{schedule.name}' triggered!", "schedule_id": schedule_id}


@router.post("/{schedule_id}/toggle", summary="Enable/disable schedule")
def toggle_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """Toggle schedule enabled/disabled"""
    schedule = db.query(ContentSchedule).filter(
        ContentSchedule.id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    schedule.enabled = not schedule.enabled
    db.commit()

    status = "enabled" if schedule.enabled else "disabled"
    return {"message": f"Schedule '{schedule.name}' {status}", "enabled": schedule.enabled}
