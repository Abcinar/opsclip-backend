from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.database import get_db
from models.user import User, PlanType
from models.video import CreditTransaction
from core.auth import get_current_user
import uuid

router = APIRouter()

CREDIT_PACKAGES = {
    "starter":  {"credits": 10,  "price_usd": 5.00},
    "creator":  {"credits": 30,  "price_usd": 12.00},
    "pro":      {"credits": 100, "price_usd": 35.00},
    "agency":   {"credits": 300, "price_usd": 90.00},
}

@router.get("/balance")
async def get_balance(current_user: User = Depends(get_current_user)):
    return {
        "balance": current_user.credits,
        "never_expire": True,
        "total_purchased": current_user.total_credits_purchased,
        "total_used": current_user.total_credits_used,
        "total_refunded": current_user.total_credits_refunded,
        "plan": current_user.plan,
    }

@router.get("/transactions")
async def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txns = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == current_user.id
    ).order_by(CreditTransaction.created_at.desc()).limit(50).all()

    return {"transactions": [
        {
            "id": t.id,
            "amount": t.amount,
            "type": t.type,
            "description": t.description,
            "balance_after": t.balance_after,
            "created_at": str(t.created_at),
        }
        for t in txns
    ]}

@router.post("/refund/{video_id}")
async def auto_refund(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Başarısız işlem için otomatik iade."""
    from models.video import Video
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == current_user.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.credit_refunded:
        raise HTTPException(status_code=400, detail="Already refunded")

    current_user.credits += 1
    current_user.total_credits_refunded += 1
    video.credit_refunded = True

    txn = CreditTransaction(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        video_id=video_id,
        amount=+1,
        type="refund",
        description="Auto-refund: processing failed",
        balance_after=current_user.credits,
    )
    db.add(txn)
    db.commit()

    return {"refunded": True, "credits_returned": 1, "new_balance": current_user.credits}
