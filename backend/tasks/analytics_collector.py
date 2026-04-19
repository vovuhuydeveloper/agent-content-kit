"""
Analytics Collector — Celery tasks to fetch video metrics from platforms.
Runs periodically via Celery Beat to update VideoAnalytics records.
"""

import logging
from datetime import datetime, timezone

try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(func):
            func.delay = lambda *a, **kw: func(*a, **kw)
            return func
        if args and callable(args[0]):
            return decorator(args[0])
        return decorator

logger = logging.getLogger("tasks.analytics")


@shared_task(name="analytics.collect_all")
def collect_all_analytics():
    """
    Collect analytics for all published videos.
    Runs daily via Celery Beat.
    """
    from backend.core.database import SessionLocal
    from backend.models.analytics import VideoAnalytics

    db = SessionLocal()
    try:
        # Get all videos that have been published
        videos = db.query(VideoAnalytics).filter(
            VideoAnalytics.post_id != "",
            VideoAnalytics.post_id.isnot(None),
        ).all()

        updated = 0
        for video in videos:
            try:
                metrics = _fetch_platform_metrics(
                    platform=video.platform,
                    post_id=video.post_id,
                )
                if metrics:
                    video.views = metrics.get("views", video.views)
                    video.likes = metrics.get("likes", video.likes)
                    video.comments = metrics.get("comments", video.comments)
                    video.shares = metrics.get("shares", video.shares)
                    video.engagement_rate = _calc_engagement(metrics)
                    video.last_fetched_at = datetime.now(timezone.utc)

                    # Append to history
                    history = video.metrics_history or []
                    history.append({
                        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "views": video.views,
                        "likes": video.likes,
                    })
                    video.metrics_history = history[-90:]  # Keep last 90 days

                    updated += 1
            except Exception as e:
                logger.warning(f"Failed to collect for {video.platform}/{video.post_id}: {e}")

        db.commit()
        logger.info(f"📊 Updated analytics for {updated}/{len(videos)} videos")
        return {"updated": updated, "total": len(videos)}

    except Exception as e:
        logger.error(f"Analytics collection failed: {e}")
        raise
    finally:
        db.close()


@shared_task(name="analytics.create_record")
def create_analytics_record(
    job_id: str,
    script_id: int,
    platform: str,
    post_id: str = "",
    post_url: str = "",
    variant: str = "",
):
    """Create an analytics record for a newly published video"""
    from backend.core.database import SessionLocal
    from backend.models.analytics import VideoAnalytics
    from backend.models.base import generate_uuid

    db = SessionLocal()
    try:
        record = VideoAnalytics(
            id=generate_uuid(),
            job_id=job_id,
            script_id=script_id,
            platform=platform,
            post_id=post_id,
            post_url=post_url,
            variant=variant,
        )
        db.add(record)
        db.commit()
        logger.info(f"📊 Analytics record created: {platform}/{post_id}")
    except Exception as e:
        logger.error(f"Failed to create analytics record: {e}")
    finally:
        db.close()


def _fetch_platform_metrics(platform: str, post_id: str) -> dict:
    """
    Fetch metrics from platform API.

    TODO: Implement real API calls when OAuth is connected.
    Currently returns None (no-op).
    """
    if platform == "youtube":
        return _fetch_youtube_metrics(post_id)
    elif platform == "tiktok":
        return _fetch_tiktok_metrics(post_id)
    elif platform == "facebook":
        return _fetch_facebook_metrics(post_id)
    return None


def _fetch_youtube_metrics(video_id: str) -> dict:
    """Fetch YouTube video stats via Data API v3"""
    try:
        import os

        from googleapiclient.discovery import build

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return None

        youtube = build("youtube", "v3", developerKey=api_key)
        response = youtube.videos().list(
            part="statistics",
            id=video_id,
        ).execute()

        items = response.get("items", [])
        if items:
            stats = items[0]["statistics"]
            return {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "shares": 0,  # YouTube API doesn't expose shares
            }
    except Exception as e:
        logger.warning(f"YouTube metrics fetch failed: {e}")
    return None


def _fetch_tiktok_metrics(post_id: str) -> dict:
    """Fetch TikTok video stats — requires OAuth access token"""
    # TODO: Implement with TikTok Content API
    logger.debug(f"TikTok metrics not yet implemented for {post_id}")
    return None


def _fetch_facebook_metrics(post_id: str) -> dict:
    """Fetch Facebook video stats via Graph API"""
    # TODO: Implement with Facebook Graph API
    logger.debug(f"Facebook metrics not yet implemented for {post_id}")
    return None


def _calc_engagement(metrics: dict) -> float:
    """Calculate engagement rate"""
    views = metrics.get("views", 0)
    if views == 0:
        return 0.0
    interactions = (
        metrics.get("likes", 0) +
        metrics.get("comments", 0) +
        metrics.get("shares", 0)
    )
    return round((interactions / views) * 100, 2)
