from sqlalchemy import select
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User, UserRole, AccountStatus


def main():
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        raise SystemExit("Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD in .env first")
    db = SessionLocal()
    try:
        email = settings.bootstrap_admin_email.lower()
        if db.scalar(select(User).where(User.email == email)):
            print("An account with this email already exists; no changes made.")
            return
        admin = User(member_id="WAL-ADMIN-000001", full_name="WALOMA Administrator", email=email,
                     phone="N/A", password_hash=hash_password(settings.bootstrap_admin_password),
                     role=UserRole.ADMIN, status=AccountStatus.APPROVED, is_active=True)
        db.add(admin)
        db.commit()
        print(f"Administrator created: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
