"""
Schedule Tasks — Celery tasks for automated content calendar.
Checks for due schedules and triggers content pipelines.
"""

import logging
from datetime import datetime, timedelta, timezone

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

logger = logging.getLogger("tasks.schedule")


def calculate_next_run(cron_expression: str, tz_name: str = "Asia/Ho_Chi_Minh") -> datetime:
    """
    Calculate next run time from a cron expression.
    Simple parser for: minute hour day_of_month month day_of_week
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    parts = cron_expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expression}")

    minute, hour, dom, month, dow = parts

    # Simple implementation: find next matching time
    # Supports: specific numbers and * (wildcard)
    int(minute) if minute != "*" else now.minute
    int(hour) if hour != "*" else now.hour

    # Start from next minute
    candidate = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

    for _ in range(7 * 24 * 60):  # Search up to 1 week
        matches = True

        if minute != "*" and candidate.minute != int(minute):
            matches = False
        if hour != "*" and candidate.hour != int(hour):
            matches = False
        if dom != "*" and candidate.day != int(dom):
            matches = False
        if month != "*" and candidate.month != int(month):
            matches = False
        if dow != "*":
            # 0=Monday in Python, but cron 0=Sunday
            cron_dow = int(dow)
            python_dow = (cron_dow - 1) % 7  # Convert cron to Python
            if candidate.weekday() != python_dow:
                matches = False

        if matches:
            return candidate.astimezone(timezone.utc)

        candidate += timedelta(minutes=1)

    # Fallback: 1 week from now
    return now + timedelta(weeks=1)


@shared_task(name="schedule.check_scheduled_jobs")
def check_scheduled_jobs():
    """
    Check for due scheduled jobs and trigger them.
    Runs every minute via Celery Beat.
    """
    from backend.core.database import SessionLocal
    from backend.models.schedule import ContentSchedule

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Find enabled schedules that are due
        due_schedules = db.query(ContentSchedule).filter(
            ContentSchedule.enabled,
            ContentSchedule.next_run_at <= now,
        ).all()

        for schedule in due_schedules:
            logger.info(f"⏰ Triggering scheduled job: {schedule.name}")
            try:
                run_scheduled_job.delay(schedule.id)
            except Exception as e:
                logger.error(f"Failed to trigger schedule {schedule.id}: {e}")
                schedule.error_message = str(e)

            # Update next_run immediately to prevent double-trigger
            try:
                schedule.next_run_at = calculate_next_run(
                    schedule.cron_expression, schedule.timezone
                )
            except Exception:
                schedule.next_run_at = now + timedelta(hours=24)

            db.commit()

        if due_schedules:
            logger.info(f"Triggered {len(due_schedules)} scheduled jobs")

    except Exception as e:
        logger.error(f"Schedule check failed: {e}")
    finally:
        db.close()


@shared_task(
    name="schedule.run_scheduled_job",
    bind=True,
    max_retries=0,
    queue="processing",
    time_limit=1800,
)
def run_scheduled_job(self, schedule_id: str):
    """
    Create and run a content job from a schedule template.
    """
    from backend.core.database import SessionLocal
    from backend.models.base import generate_uuid
    from backend.models.content_job import ContentJob
    from backend.models.schedule import ContentSchedule
    from backend.tasks.agent_tasks import run_content_pipeline

    db = SessionLocal()
    try:
        schedule = db.query(ContentSchedule).filter(
            ContentSchedule.id == schedule_id
        ).first()

        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return

        # Create a new content job from schedule template
        job_id = generate_uuid()
        job = ContentJob(
            id=job_id,
            source_url=schedule.source_url,
            source_type=schedule.source_type,
            language=schedule.language,
            video_count=schedule.video_count,
            platforms=schedule.platforms,
            niche=schedule.niche,
            competitor_urls=schedule.competitor_urls,
            character_images=schedule.character_images,
            status="pending",
        )
        db.add(job)

        # Update schedule tracking
        schedule.last_run_at = datetime.now(timezone.utc)
        schedule.run_count = (schedule.run_count or 0) + 1
        schedule.last_job_id = job_id

        # Calculate next run
        try:
            schedule.next_run_at = calculate_next_run(
                schedule.cron_expression, schedule.timezone
            )
        except Exception:
            schedule.next_run_at = datetime.now(timezone.utc) + timedelta(hours=24)

        db.commit()

        # Trigger the pipeline
        job_input = {
            "source_url": schedule.source_url,
            "source_type": schedule.source_type,
            "language": schedule.language,
            "video_count": schedule.video_count,
            "platforms": schedule.platforms or ["tiktok"],
            "niche": schedule.niche or "",
            "competitor_urls": schedule.competitor_urls or [],
            "character_images": schedule.character_images or [],
        }

        run_content_pipeline.delay(job_id, job_input)

        logger.info(f"✅ Scheduled job created: {job_id} from schedule {schedule.name}")

        # Notify via Telegram
        try:
            from backend.agents.notifier import TelegramNotifier
            TelegramNotifier().send_message(
                f"📅 <b>Scheduled job started!</b>\n"
                f"📋 Schedule: {schedule.name}\n"
                f"🆔 Job: <code>{job_id}</code>\n"
                f"🔗 Source: {schedule.source_url[:50]}"
            )
        except Exception:
            pass

        return {"job_id": job_id, "schedule_id": schedule_id}

    except Exception as e:
        logger.error(f"Scheduled job failed for {schedule_id}: {e}")
        if schedule:
            schedule.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()
