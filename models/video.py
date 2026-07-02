from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from db.database import Base
import uuid
import enum

class VideoStatus(str, enum.Enum):
    queued     = "queued"
    downloading = "downloading"
    transcribing = "transcribing"
    analyzing  = "analyzing"
    cutting    = "cutting"
    rendering  = "rendering"
    done       = "done"
    failed     = "failed"

class Video(Base):
    __tablename__ = "videos"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id     = Column(String, ForeignKey("users.id"), nullable=False)
    title       = Column(String, nullable=True)
    source_url  = Column(String, nullable=True)      # YouTube URL
    source_path = Column(String, nullable=True)      # Uploaded file path
    language    = Column(String, default="ar")
    command     = Column(Text, nullable=True)        # Kullanıcı komutu
    status      = Column(Enum(VideoStatus), default=VideoStatus.queued)
    progress    = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    transcript  = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    credit_charged = Column(Boolean, default=False)
    credit_refunded = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

class Clip(Base):
    __tablename__ = "clips"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id    = Column(String, ForeignKey("videos.id"), nullable=False)
    user_id     = Column(String, ForeignKey("users.id"), nullable=False)
    title       = Column(String, nullable=True)
    start_time  = Column(Float, nullable=False)
    end_time    = Column(Float, nullable=False)
    duration    = Column(Float, nullable=False)
    viral_score = Column(Integer, default=0)
    language    = Column(String, default="ar")
    output_path = Column(String, nullable=True)      # S3 path
    output_url  = Column(String, nullable=True)      # CDN URL
    subtitle_path = Column(String, nullable=True)
    is_downloaded = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id     = Column(String, ForeignKey("users.id"), nullable=False)
    video_id    = Column(String, nullable=True)
    amount      = Column(Integer, nullable=False)    # + ekle, - çıkar
    type        = Column(String, nullable=False)     # purchase, usage, refund
    description = Column(String, nullable=True)
    balance_after = Column(Integer, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
