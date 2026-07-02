"""
Admin API — Sadece admin ve manager rolü erişebilir.
Tüm kullanıcılar, videolar, klipler, istatistikler.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from db.database import get_db
from models.user import User, RoleType, PlanType
from models.video import Video, Clip, CreditTransaction
from core.auth import get_current_user, get_admin_user

router = APIRouter()

# ── DASHBOARD İSTATİSTİKLERİ ──────────────────────────────────────────────────
@router.get("/stats")
async def admin_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    total_users   = db.query(func.count(User.id)).scalar()
    active_users  = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    total_videos  = db.query(func.count(Video.id)).scalar()
    total_clips   = db.query(func.count(Clip.id)).scalar()
    total_credits = db.query(func.sum(User.total_credits_purchased)).scalar() or 0

    plan_breakdown = db.query(User.plan, func.count(User.id)).group_by(User.plan).all()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_videos_processed": total_videos,
        "total_clips_created": total_clips,
        "total_credits_sold": total_credits,
        "plan_breakdown": {str(p): c for p, c in plan_breakdown},
    }

# ── KULLANICI YÖNETİMİ ────────────────────────────────────────────────────────
@router.get("/users")
async def list_users(
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    plan: Optional[str] = None,
    role: Optional[str] = None,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(User)
    if search:
        q = q.filter(User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%"))
    if plan:
        q = q.filter(User.plan == plan)
    if role:
        q = q.filter(User.role == role)

    total = q.count()
    users = q.order_by(User.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
        "users": [_user_dict(u) for u in users]
    }

@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_dict(user, full=True)

class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    plan: Optional[str] = None
    credits: Optional[int] = None
    is_active: Optional[bool] = None

@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Sadece süper admin (admin) manager atayabilir
    if req.role and admin.role != RoleType.admin:
        raise HTTPException(status_code=403, detail="Only super admin can change roles")

    if req.role:      user.role = req.role
    if req.plan:      user.plan = req.plan
    if req.credits is not None:
        diff = req.credits - user.credits
        user.credits = req.credits
        if diff > 0:
            user.total_credits_purchased += diff
    if req.is_active is not None: user.is_active = req.is_active

    db.commit()
    return {"message": "User updated", "user": _user_dict(user)}

@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == RoleType.admin:
        raise HTTPException(status_code=403, detail="Cannot ban admin")
    user.is_active = False
    db.commit()
    return {"message": f"User {user.email} banned"}

@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()
    return {"message": f"User {user.email} unbanned"}

@router.post("/users/{user_id}/add-credits")
async def add_credits(
    user_id: str,
    amount: int,
    reason: str = "Manual credit addition by admin",
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    import uuid
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.credits += amount
    user.total_credits_purchased += amount

    txn = CreditTransaction(
        id=str(uuid.uuid4()),
        user_id=user_id,
        amount=amount,
        type="manual",
        description=f"Admin ({admin.email}): {reason}",
        balance_after=user.credits,
    )
    db.add(txn)
    db.commit()
    return {"message": f"{amount} credits added", "new_balance": user.credits}

@router.post("/users/{user_id}/make-admin")
async def make_admin(
    user_id: str,
    role: str = "manager",
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Kullanıcıya admin/manager rolü ver. Sadece süper admin yapabilir."""
    if admin.role != RoleType.admin:
        raise HTTPException(status_code=403, detail="Only super admin can assign admin roles")
    if role not in ["admin", "manager"]:
        raise HTTPException(status_code=400, detail="Role must be admin or manager")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    db.commit()
    return {"message": f"{user.email} is now {role}"}

# ── VİDEO / KLİP YÖNETİMİ ────────────────────────────────────────────────────
@router.get("/videos")
async def list_all_videos(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(Video)
    if status:
        q = q.filter(Video.status == status)
    total = q.count()
    videos = q.order_by(Video.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()
    return {
        "total": total,
        "videos": [{"id": v.id, "user_id": v.user_id, "status": v.status,
                    "language": v.language, "created_at": str(v.created_at)} for v in videos]
    }

@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    db.delete(video)
    db.commit()
    return {"message": "Video deleted"}

# ── HELPER ────────────────────────────────────────────────────────────────────
def _user_dict(u: User, full: bool = False) -> dict:
    d = {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "plan": u.plan,
        "credits": u.credits,
        "is_active": u.is_active,
        "created_at": str(u.created_at),
        "last_login": str(u.last_login) if u.last_login else None,
    }
    if full:
        d.update({
            "total_credits_purchased": u.total_credits_purchased,
            "total_credits_used": u.total_credits_used,
            "total_credits_refunded": u.total_credits_refunded,
        })
    return d
