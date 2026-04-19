"""
Content Jobs API — REST endpoint để submit & monitor content jobs.
"""

import logging
import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.base import generate_uuid
from backend.models.content_job import ContentJob

logger = logging.getLogger("api.content_jobs")

router = APIRouter(prefix="/content-jobs", tags=["Content Jobs"])


@router.post("/", summary="Submit a new content job")
async def create_content_job(
    source_url: str = Form("", description="URL nguồn content (web/video)"),
    language: str = Form("vi", description="Language: vi or en"),
    video_count: int = Form(3, description="Số video cần tạo"),
    aspect_ratio: str = Form("9:16", description="Video aspect ratio: 9:16, 16:9, 1:1"),
    platforms: str = Form("tiktok,youtube", description="Comma-separated platforms"),
    niche: str = Form("", description="Chủ đề/niche (optional)"),
    competitor_urls: str = Form("", description="Comma-separated competitor URLs (optional)"),
    character_files: List[UploadFile] = File(None, description="2D character images"),
    source_document: UploadFile = File(None, description="Source document (PDF/DOCX/TXT)"),
    db: Session = Depends(get_db),
):
    """
    Submit a content creation job.

    Source can be either:
    - A URL (source_url) — web page or video link
    - A document (source_document) — PDF, DOCX, or TXT file

    The pipeline will:
    1. Fetch content from source_url or parse uploaded document
    2. Analyze competitors (if provided)
    3. Generate video scripts
    4. Create voiceover
    5. Render videos with character overlay
    6. Create thumbnails
    7. Quality review
    8. Publish to platforms
    """
    job_id = generate_uuid()

    # Parse comma-separated fields
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]
    competitor_list = [u.strip() for u in competitor_urls.split(",") if u.strip()] if competitor_urls else []

    # Save uploaded character images
    char_dir = f"data/characters/{job_id}"
    os.makedirs(char_dir, exist_ok=True)

    character_paths = []
    if character_files:
        for i, file in enumerate(character_files):
            if file.filename:
                ext = os.path.splitext(file.filename)[1] or ".png"
                save_path = f"{char_dir}/char_{i}{ext}"
                with open(save_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                character_paths.append(save_path)

    # Handle document upload
    source_document_path = ""
    source_type = "web"
    if source_document and source_document.filename:
        doc_dir = f"data/documents/{job_id}"
        os.makedirs(doc_dir, exist_ok=True)
        doc_ext = os.path.splitext(source_document.filename)[1] or ".txt"
        doc_save_path = f"{doc_dir}/source{doc_ext}"
        with open(doc_save_path, "wb") as f:
            doc_content = await source_document.read()
            f.write(doc_content)
        source_document_path = doc_save_path
        source_type = "document"
        if not source_url:
            source_url = source_document.filename

    # Validate: must have either URL or document
    if not source_url and not source_document_path:
        raise HTTPException(
            status_code=400,
            detail="Either source_url or source_document is required"
        )

    # Create job record
    job = ContentJob(
        id=job_id,
        source_url=source_url,
        source_type=source_type,
        language=language,
        video_count=video_count,
        platforms=platform_list,
        niche=niche,
        competitor_urls=competitor_list,
        character_images=character_paths,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Trigger async pipeline
    from backend.tasks.agent_tasks import run_content_pipeline

    job_input = {
        "source_url": source_url,
        "source_type": source_type,
        "source_document_path": source_document_path,
        "language": language,
        "video_count": video_count,
        "aspect_ratio": aspect_ratio,
        "platforms": platform_list,
        "niche": niche,
        "competitor_urls": competitor_list,
        "character_images": character_paths,
    }

    run_content_pipeline.delay(job_id, job_input)

    logger.info(f"Job {job_id} created and queued")

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Job queued! Pipeline will start shortly.",
        "monitor_url": f"/api/v1/content-jobs/{job_id}",
    }


@router.get("/{job_id}", summary="Get job status")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get the current status and results of a content job"""
    job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "source_url": job.source_url,
        "language": job.language,
        "platforms": job.platforms,
        "progress": job.progress,
        "current_agent": job.current_agent,
        "scripts_count": job.scripts_count,
        "videos_count": job.videos_count,
        "published_count": job.published_count,
        "elapsed_seconds": job.elapsed_seconds,
        "error": job.error_message or None,
        "pipeline_result": job.pipeline_result,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/", summary="List all jobs")
def list_jobs(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all content jobs, newest first"""
    query = db.query(ContentJob)

    if status:
        query = query.filter(ContentJob.status == status)

    total = query.count()
    jobs = query.order_by(ContentJob.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "jobs": [
            {
                "job_id": j.id,
                "status": j.status,
                "source_url": j.source_url,
                "videos_count": j.videos_count,
                "published_count": j.published_count,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ],
    }


@router.delete("/{job_id}", summary="Delete a job")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Delete a content job and its data"""
    job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Clean up files
    job_dir = f"data/jobs/{job_id}"
    if os.path.exists(job_dir):
        shutil.rmtree(job_dir)

    char_dir = f"data/characters/{job_id}"
    if os.path.exists(char_dir):
        shutil.rmtree(char_dir)

    db.delete(job)
    db.commit()

    return {"message": f"Job {job_id} deleted"}


@router.post("/{job_id}/approve", summary="Approve job for publishing")
def approve_job(job_id: str, db: Session = Depends(get_db)):
    """Approve a job that's awaiting approval — triggers PublisherAgent"""
    job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "awaiting_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Job status is '{job.status}', expected 'awaiting_approval'"
        )

    job.status = "approved"
    db.commit()

    # Trigger publisher
    from backend.tasks.agent_tasks import run_publisher
    run_publisher.delay(job_id)

    return {"job_id": job_id, "status": "approved", "message": "Publishing started!"}


@router.post("/{job_id}/reject", summary="Reject a job")
def reject_job(job_id: str, db: Session = Depends(get_db)):
    """Reject a job — won't be published"""
    job = db.query(ContentJob).filter(ContentJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "rejected"
    db.commit()

    return {"job_id": job_id, "status": "rejected", "message": "Job rejected"}


@router.get("/{job_id}/files", summary="List output files for a job")
def list_job_files(job_id: str):
    """List all output files (videos, thumbnails, scripts, audio) for a job"""
    from pathlib import Path

    job_dir = Path(f"data/jobs/{job_id}")
    if not job_dir.exists():
        return {"files": [], "job_dir": str(job_dir)}

    files = []
    MEDIA_EXTS = {
        ".mp4": "video", ".webm": "video", ".avi": "video", ".mov": "video",
        ".mp3": "audio", ".wav": "audio",
        ".jpg": "image", ".jpeg": "image", ".png": "image", ".webp": "image",
        ".json": "data",
    }

    for f in sorted(job_dir.rglob("*")):
        if f.is_file() and not f.name.startswith("."):
            ext = f.suffix.lower()
            file_type = MEDIA_EXTS.get(ext, "other")
            rel_path = str(f.relative_to(job_dir))
            files.append({
                "name": f.name,
                "path": rel_path,
                "type": file_type,
                "size": f.stat().st_size,
                "url": f"/api/v1/content-jobs/{job_id}/files/{rel_path}",
            })

    return {"files": files, "job_dir": str(job_dir)}


@router.get("/{job_id}/files/{file_path:path}", summary="Serve a job output file")
def serve_job_file(job_id: str, file_path: str):
    """Serve a specific file from job output directory"""
    from pathlib import Path

    from fastapi.responses import FileResponse

    # Security: prevent path traversal
    safe_path = Path(f"data/jobs/{job_id}") / file_path
    if not safe_path.resolve().is_relative_to(Path(f"data/jobs/{job_id}").resolve()):
        raise HTTPException(400, "Invalid file path")

    if not safe_path.exists():
        raise HTTPException(404, "File not found")

    # Determine media type
    ext = safe_path.suffix.lower()
    media_types = {
        ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
        ".mp3": "audio/mpeg", ".wav": "audio/wav",
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
        ".json": "application/json",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(str(safe_path), media_type=media_type)

