from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, Enum
from sqlalchemy.sql import func
from db.database import Base
import uuid
import enum

class PlanType(str, enum.Enum):
    free    = "free"
    starter = "starter"
    pro     = "pro"
    agency  = "agency"

class RoleType(str, enum.Enum):
    user    = "user"
    admin   = "admin"
    manager = "manager"

class User(Base):
    __tablename__ = "users"

    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email         = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name     = Column(String, nullable=True)
    is_active     = Column(Boolean, default=True)
    is_verified   = Column(Boolean, default=False)
    role          = Column(Enum(RoleType), default=RoleType.user)
    plan          = Column(Enum(PlanType), default=PlanType.free)
    credits       = Column(Integer, default=3)      # Free plan: 3 kredi
    total_credits_purchased = Column(Integer, default=0)
    total_credits_used      = Column(Integer, default=0)
    total_credits_refunded  = Column(Integer, default=0)
    preferred_language = Column(String, default="en")
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())
    last_login    = Column(DateTime(timezone=True), nullable=True)
