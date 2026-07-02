from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from db.database import get_db
from models.user import User, PlanType, RoleType
from core.auth import hash_password, verify_password, create_token, get_current_user
from datetime import datetime
import uuid

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        credits=3,      # Free plan: 3 kredi
        plan=PlanType.free,
        role=RoleType.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token({"sub": user.id})
    return {"access_token": token, "user": _user_dict(user)}

@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_token({"sub": user.id})
    return {"access_token": token, "user": _user_dict(user)}

@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return _user_dict(current_user)

@router.post("/logout")
async def logout():
    return {"message": "Logged out"}

def _user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "plan": u.plan,
        "credits": u.credits,
        "created_at": str(u.created_at),
    }
