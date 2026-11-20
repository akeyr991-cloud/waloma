from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import User


def next_member_id(db: Session) -> str:
    """Create a readable, unique ID; database uniqueness remains the final safeguard."""
    year = datetime.now(timezone.utc).year
    prefix = f"WAL-{year}-"
    last_id = db.scalar(select(func.max(User.member_id)).where(User.member_id.like(f"{prefix}%")))
    sequence = int(last_id.rsplit("-", 1)[1]) + 1 if last_id else 1
    return f"{prefix}{sequence:06d}"
