"""
İlk kurulumda çalıştır: python db/migrations.py
"""
from db.database import Base, engine
from models.user import User
from models.video import Video, Clip, CreditTransaction

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("✅ Tüm tablolar oluşturuldu")

def create_super_admin(email: str, password: str):
    from db.database import SessionLocal
    from models.user import RoleType, PlanType
    from core.auth import hash_password
    import uuid
    db = SessionLocal()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"⚠️  {email} zaten var")
        return
    admin = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password(password),
        full_name="Super Admin",
        role=RoleType.admin,
        plan=PlanType.agency,
        credits=9999,
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    db.commit()
    print(f"✅ Super admin oluşturuldu: {email}")

if __name__ == "__main__":
    create_tables()
    # İlk admin hesabını oluştur — şifreyi değiştir!
    create_super_admin("admin@opsclip.com", "ChangeMe123!")
