"""
Video Analytics model — Track video performance across platforms.
"""

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

from backend.models.base import BaseModel


class VideoAnalytics(BaseModel):
    """Performance metrics for a published video"""

    __tablename__ = "video_analytics"

    # Reference
    job_id = Column(String(36), nullable=False, index=True, comment="ContentJob ID")
    script_id = Column(Integer, default=1)
    platform = Column(String(20), nullable=False, comment="tiktok|youtube|facebook|instagram")
    post_id = Column(String(200), default="", comment="Platform post/video ID")
    post_url = Column(String(2048), default="")

    # Metrics (updated periodically)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    watch_time_seconds = Column(Float, default=0.0)
    avg_watch_percentage = Column(Float, default=0.0)

    # Engagement
    engagement_rate = Column(Float, default=0.0)
    click_through_rate = Column(Float, default=0.0)

    # Follower impact
    followers_gained = Column(Integer, default=0)

    # A/B test tracking
    variant = Column(String(10), default="", comment="A/B test variant label")

    # History snapshots
    metrics_history = Column(JSON, default=list, comment="Daily metric snapshots")

    # Last update
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "script_id": self.script_id,
            "platform": self.platform,
            "post_id": self.post_id,
            "post_url": self.post_url,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "engagement_rate": self.engagement_rate,
            "variant": self.variant,
            "last_fetched_at": self.last_fetched_at.isoformat() if self.last_fetched_at else None,
        }
