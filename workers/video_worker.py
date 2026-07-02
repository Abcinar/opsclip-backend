"""
Celery Worker — Asenkron video işleme
Sıra: indir → ses çıkar → transkribe → klip seç → kes → yükle → bildir
"""
import asyncio
from celery import shared_task
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.video import Video, Clip, VideoStatus
from models.user import User
from services.video_service import download_youtube, extract_audio, cut_clip, get_video_duration, cleanup
from services.asr_service import transcribe_audio
from services.clip_selector import select_clips
from services.storage_service import upload_clip
from datetime import datetime
import uuid
import os

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def update_video(db: Session, video_id: str, **kwargs):
    db.query(Video).filter(Video.id == video_id).update(kwargs)
    db.commit()

@shared_task(bind=True, max_retries=2)
def process_video_task(self, video_id: str):
    db = SessionLocal()
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        return

    try:
        # 1 — İndir
        update_video(db, video_id, status=VideoStatus.downloading, progress=5, current_step="Downloading video...")
        if video.source_url:
            audio_path = run_async(download_youtube(video.source_url, video_id))
            video_path = audio_path.replace(".mp3", ".mp4")
            # Tam video da indir (klip kesme için)
            run_async(download_youtube_video(video.source_url, video_id))
        else:
            audio_path = run_async(extract_audio(video.source_path, video_id))
            video_path = video.source_path

        # 2 — Transkribe
        update_video(db, video_id, status=VideoStatus.transcribing, progress=25, current_step="Transcribing audio...")
        transcript_data = run_async(transcribe_audio(audio_path, video.language))
        update_video(db, video_id, transcript=transcript_data["text"], progress=45)

        # 3 — Klip Seç
        update_video(db, video_id, status=VideoStatus.analyzing, progress=50, current_step="AI analyzing content...")
        clips_data = run_async(select_clips(
            transcript_data["segments"],
            language=video.language,
            user_command=video.command,
            max_clips=8
        ))

        # 4 — Kes ve Yükle
        update_video(db, video_id, status=VideoStatus.cutting, progress=60, current_step="Cutting clips...")
        created_clips = []
        for i, clip_data in enumerate(clips_data):
            clip_id = str(uuid.uuid4())
            out_path = f"/tmp/luminaclip/{clip_id}.mp4"

            run_async(cut_clip(video_path, clip_data["start"], clip_data["end"], out_path, video.language))
            update_video(db, video_id, progress=60 + int(30 * (i+1) / len(clips_data)))

            # S3'e yükle
            clip_url = run_async(upload_clip(out_path, clip_id))

            clip = Clip(
                id=clip_id,
                video_id=video_id,
                user_id=video.user_id,
                title=clip_data["title"],
                start_time=clip_data["start"],
                end_time=clip_data["end"],
                duration=clip_data["end"] - clip_data["start"],
                viral_score=clip_data["viral_score"],
                language=video.language,
                output_url=clip_url,
                output_path=f"clips/{clip_id}.mp4"
            )
            db.add(clip)
            created_clips.append(clip)
            os.remove(out_path)

        db.commit()

        # 5 — Tamamlandı
        update_video(db, video_id,
            status=VideoStatus.done,
            progress=100,
            current_step="Done!",
            completed_at=datetime.utcnow()
        )

    except Exception as e:
        # Hata durumunda kredi iade et
        update_video(db, video_id,
            status=VideoStatus.failed,
            error_message=str(e),
            credit_refunded=True
        )
        # Kullanıcıya krediyi geri ver
        db.query(User).filter(User.id == video.user_id).update({
            User.credits: User.credits + 1
        })
        db.commit()
        raise

    finally:
        run_async(cleanup(video_id))
        db.close()

async def download_youtube_video(url: str, job_id: str) -> str:
    """Tam video indir (kesme için)."""
    import yt_dlp
    output = f"/tmp/luminaclip/{job_id}.mp4"
    opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "outtmpl": output,
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return output
