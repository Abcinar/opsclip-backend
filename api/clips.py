from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from models.user import User
from models.video import Clip
from core.auth import get_current_user
from services.storage_service import get_presigned_url

router = APIRouter()

@router.get("/")
async def list_clips(
    language: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from typing import Optional
    q = db.query(Clip).filter(Clip.user_id == current_user.id)
    if language:
        q = q.filter(Clip.language == language)
    clips = q.order_by(Clip.viral_score.desc()).all()

    return {"clips": [
        {
            "id": c.id,
            "video_id": c.video_id,
            "title": c.title,
            "duration": round(c.duration, 1),
            "viral_score": c.viral_score,
            "language": c.language,
            "output_url": c.output_url,
            "created_at": str(c.created_at),
        }
        for c in clips
    ], "total": len(clips)}

@router.get("/{clip_id}/download")
async def download_clip(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clip = db.query(Clip).filter(Clip.id == clip_id, Clip.user_id == current_user.id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    clip.download_count += 1
    clip.is_downloaded = True
    db.commit()

    url = await get_presigned_url(clip_id, expires=3600)
    return {"download_url": url, "expires_in": 3600}

@router.post("/{clip_id}/regenerate")
async def regenerate_clip(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clip = db.query(Clip).filter(Clip.id == clip_id, Clip.user_id == current_user.id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    # Kredi ödenmez — regenerate ücretsiz
    return {"message": "Clip queued for regeneration", "credit_charged": False}

from typing import Optional
