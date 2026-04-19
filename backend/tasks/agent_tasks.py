"""
Background tasks for the Agent Pipeline.
Runs async via Celery if available, otherwise via subprocess.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime, timezone

try:
    from celery import shared_task
except ImportError:
    # Celery not installed — run tasks in isolated subprocess to avoid segfaults
    import threading

    def shared_task(*args, **kwargs):
        bind = kwargs.get('bind', False)

        def decorator(func):
            def delay(*a, **kw):
                if bind:
                    thread = threading.Thread(target=func, args=(None, *a), kwargs=kw, daemon=True)
                else:
                    thread = threading.Thread(target=func, args=a, kwargs=kw, daemon=True)
                thread.start()
            func.delay = delay
            return func
        if args and callable(args[0]):
            return decorator(args[0])
        return decorator

logger = logging.getLogger("tasks.agent")


@shared_task(
    name="agents.run_content_pipeline",
    bind=True,
    max_retries=0,
    queue="processing",
    time_limit=1800,  # 30 minutes max
    soft_time_limit=1500,
)
def run_content_pipeline(self, job_id: str, job_input: dict):
    """
    Chạy toàn bộ agent pipeline cho 1 content job.
    Uses subprocess to avoid Python segfaults from LibreSSL+httpx.
    """
    import json as _json

    logger.info(f"🚀 Starting pipeline for job {job_id}")

    # Run pipeline in isolated subprocess to prevent segfaults
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    runner_script = os.path.join(project_root, "backend", "tasks", "pipeline_runner.py")

    cmd = [
        sys.executable, runner_script,
        job_id,
        _json.dumps(job_input),
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ},
        )
        stdout, stderr = proc.communicate(timeout=1800)  # 30 min max

        if proc.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")[-500:]
            logger.error(f"❌ Pipeline subprocess failed for job {job_id}: {error_msg}")
        else:
            logger.info(f"✅ Pipeline subprocess completed for job {job_id}")

        return {"job_id": job_id, "returncode": proc.returncode}

    except subprocess.TimeoutExpired:
        proc.kill()
        logger.error(f"❌ Pipeline timeout for job {job_id}")
        _mark_job_failed(job_id, "Pipeline timed out after 30 minutes")
        return {"job_id": job_id, "returncode": -1}

    except Exception as e:
        logger.error(f"❌ Pipeline subprocess error for job {job_id}: {e}")
        _mark_job_failed(job_id, str(e)[:500])
        return {"job_id": job_id, "returncode": -1}


def _mark_job_failed(job_id: str, error_msg: str):
    """Mark a job as failed in the database"""
    from backend.core.database import SessionLocal
    from backend.models.content_job import ContentJob
    db = SessionLocal()
    try:
        job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = error_msg
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@shared_task(name="agents.check_job_status")
def check_job_status(job_id: str) -> dict:
    """Check status of a content job"""
    from backend.core.database import SessionLocal
    from backend.models.content_job import ContentJob

    db = SessionLocal()
    try:
        job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
        if job:
            return job.to_dict()
        return {"error": "Job not found"}
    finally:
        db.close()


@shared_task(
    name="agents.run_publisher",
    bind=True,
    max_retries=0,
    queue="processing",
    time_limit=600,
)
def run_publisher(self, job_id: str):
    """
    Resume pipeline from PublisherAgent after Telegram approval.
    Loads checkpoint, runs only PublisherAgent.
    """
    from backend.agents.pipeline import Pipeline
    from backend.core.database import SessionLocal
    from backend.models.content_job import ContentJob

    logger.info(f"🚀 Publishing approved job {job_id}")

    db = SessionLocal()
    try:
        job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = "publishing"
        db.commit()

        # Resume pipeline from PublisherAgent
        pipeline = Pipeline.default()
        job_input = {
            "source_url": job.source_url,
            "language": job.language,
            "video_count": job.video_count,
            "platforms": job.platforms or ["tiktok"],
            "niche": job.niche or "",
            "competitor_urls": job.competitor_urls or [],
            "character_images": job.character_images or [],
            "job_id": job_id,
        }

        result = pipeline.run(job_input, resume_from="PublisherAgent")

        # Update job
        job.status = result.get("pipeline_status", "completed")
        job.published_count = result.get("published_count", 0)
        job.completed_at = datetime.now(timezone.utc)

        # Merge pipeline result
        existing_result = job.pipeline_result or {}
        existing_result["publications"] = result.get("publications", [])
        job.pipeline_result = existing_result

        db.commit()

        # Send Telegram confirmation
        try:
            from backend.agents.notifier import TelegramNotifier
            notifier = TelegramNotifier()
            notifier.send_message(
                f"✅ <b>Upload hoàn tất!</b>\n"
                f"🆔 <code>{job_id}</code>\n"
                f"📹 Published: {result.get('published_count', 0)} videos"
            )
        except Exception:
            pass

        logger.info(f"✅ Publishing completed for job {job_id}")
        return {"job_id": job_id, "status": "completed"}

    except Exception as e:
        logger.error(f"❌ Publishing failed for job {job_id}: {e}")
        if job:
            job.status = "publish_failed"
            job.error_message = str(e)
            db.commit()

        try:
            from backend.agents.notifier import TelegramNotifier
            TelegramNotifier().send_message(f"❌ Upload failed: {e}")
        except Exception:
            pass
        raise

    finally:
        db.close()
