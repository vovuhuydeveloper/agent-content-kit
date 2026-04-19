"""
Standalone pipeline runner — runs as a subprocess to avoid segfaults.
Called from agent_tasks.py when Celery is not available.
"""

import json
import os
import sys

# Ensure project root in path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Load environment
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(project_root, ".env"))

import logging  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("pipeline_runner")


def run(job_id: str, job_input: dict):
    """Run the full pipeline and update the database"""
    from datetime import datetime, timezone

    from backend.agents.pipeline import Pipeline
    from backend.core.database import SessionLocal
    from backend.models.content_job import ContentJob

    db = SessionLocal()
    try:
        # Mark running
        job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
        if job:
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            try:
                db.commit()
            except Exception:
                db.rollback()

        # Run pipeline
        pipeline = Pipeline.default()
        job_input["job_id"] = job_id
        result = pipeline.run(job_input)

        # Update results
        try:
            db.rollback()
            job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
            if job:
                job.status = result.get("pipeline_status", "completed")
                job.completed_at = datetime.now(timezone.utc)
                job.elapsed_seconds = result.get("pipeline_elapsed_seconds", 0)
                job.scripts_count = result.get("scripts_count", 0)
                job.videos_count = result.get("video_count", 0)
                job.published_count = result.get("published_count", 0)
                job.pipeline_result = {
                    "agent_results": result.get("agent_results", []),
                    "videos": result.get("videos", []),
                    "publications": result.get("publications", []),
                }
                if result.get("errors"):
                    job.error_message = str(result["errors"])
                db.commit()
        except Exception as e:
            logger.warning(f"DB commit error: {e}")
            db.rollback()

        logger.info(f"✅ Pipeline completed for job {job_id}")
        print(json.dumps({"status": "ok", "job_id": job_id}))

    except Exception as e:
        logger.error(f"❌ Pipeline failed for job {job_id}: {e}")
        try:
            db.rollback()
            job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)[:500]
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            db.rollback()
        print(json.dumps({"status": "error", "job_id": job_id, "error": str(e)[:200]}))
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m backend.tasks.pipeline_runner <job_id> <job_input_json>")
        sys.exit(1)

    job_id = sys.argv[1]
    job_input = json.loads(sys.argv[2])
    run(job_id, job_input)
