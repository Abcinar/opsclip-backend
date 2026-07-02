from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from db.database import get_db
from models.user import User
from models.video import Video, VideoStatus
from core.auth import get_current_user
from core.celery_app import celery_app
import uuid, os, aiofiles

router = APIRouter()
UPLOAD_DIR = "/tmp/luminaclip/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_video(
    url: Optional[str] = Form(None),
    language: str = Form("ar"),
    command: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Kredi kontrolü
    if current_user.credits < 1:
        raise HTTPException(status_code=402, detail="Insufficient credits. Please top up.")

    if not url and not file:
        raise HTTPException(status_code=400, detail="Provide a URL or upload a file.")

    video_id = str(uuid.uuid4())
    source_path = None

    # Dosya yükleme
    if file:
        ext = file.filename.split(".")[-1]
        source_path = f"{UPLOAD_DIR}/{video_id}.{ext}"
        async with aiofiles.open(source_path, "wb") as f:
            content = await file.read()
            await f.write(content)

    # Krediyi düş
    current_user.credits -= 1
    current_user.total_credits_used += 1

    # Video kaydı oluştur
    video = Video(
        id=video_id,
        user_id=current_user.id,
        source_url=url,
        source_path=source_path,
        language=language,
        command=command,
        status=VideoStatus.queued,
        credit_charged=True,
    )
    db.add(video)
    db.commit()

    # Celery task başlat
    celery_app.send_task("workers.video_worker.process_video_task", args=[video_id])

    return {
        "video_id": video_id,
        "status": "queued",
        "message": "Processing started. Credits auto-refunded on failure.",
        "credits_remaining": current_user.credits,
    }

@router.get("/status/{video_id}")
async def get_status(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == current_user.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "video_id": video_id,
        "status": video.status,
        "progress": video.progress,
        "current_step": video.current_step,
        "error": video.error_message,
        "credit_refunded": video.credit_refunded,
    }

@router.get("/")
async def list_videos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    videos = db.query(Video).filter(Video.user_id == current_user.id).order_by(Video.created_at.desc()).limit(20).all()
    return {"videos": [
        {
            "id": v.id,
            "title": v.title or v.source_url or "Untitled",
            "status": v.status,
            "language": v.language,
            "created_at": str(v.created_at),
        }
        for v in videos
    ]}
