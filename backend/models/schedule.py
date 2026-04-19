"""
Content Schedule model — Scheduled content jobs for the content calendar.
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from backend.models.base import BaseModel


class ContentSchedule(BaseModel):
    """Scheduled content job — runs automatically via Celery Beat"""

    __tablename__ = "content_schedules"

    # Schedule config
    name = Column(String(200), nullable=False, comment="Schedule name")
    cron_expression = Column(String(100), nullable=False, default="0 9 * * 1",
                             comment="Cron: min hour day month weekday")
    timezone = Column(String(50), default="Asia/Ho_Chi_Minh")
    enabled = Column(Boolean, default=True)

    # Job template
    source_url = Column(String(2048), nullable=False, comment="URL nguồn content")
    source_type = Column(String(20), default="web", comment="web|video|document")
    language = Column(String(10), default="vi")
    niche = Column(String(200), default="")
    video_count = Column(Integer, default=3)
    platforms = Column(JSON, default=list)
    competitor_urls = Column(JSON, default=list)
    character_images = Column(JSON, default=list)

    # Tracking
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    run_count = Column(Integer, default=0)
    last_job_id = Column(String(36), default="", comment="ID of last created job")
    error_message = Column(Text, default="")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "enabled": self.enabled,
            "source_url": self.source_url,
            "language": self.language,
            "niche": self.niche,
            "video_count": self.video_count,
            "platforms": self.platforms,
            "run_count": self.run_count,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_job_id": self.last_job_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
