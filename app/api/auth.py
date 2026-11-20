
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.security import hash_password, verify_password, create_access_token
from app.db.session import get_db
from app.models import User, UserRole, AccountStatus
from app.schemas.auth import (
    RegistrationCreate,
    StaffAccountCreate,
    LoginRequest,
    UserRead,
    TokenResponse,
    StatusUpdate,
    PasswordChange,
)
from app.services.members import next_member_id

router = APIRouter(prefix="/auth", tags=["Authentication and registration"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegistrationCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        member_id=next_member_id(db),
        full_name=payload.full_name.strip(),
        email=email,
        phone=payload.phone.strip(),
        password_hash=hash_password(payload.password),
        role=UserRole.MEMBER,
        status=AccountStatus.PENDING,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Registration could not be completed; please retry",
        )
    db.refresh(user)
    return user


@router.post("/staff", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_staff_account(
    payload: StaffAccountCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    email = payload.email.lower()

    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists",
        )

    staff_role = UserRole(payload.role)

    user = User(
        member_id=next_member_id(db),
        full_name=payload.full_name.strip(),
        email=email,
        phone=payload.phone.strip(),
        password_hash=hash_password(payload.password),
        role=staff_role,
        status=AccountStatus.APPROVED,
        is_active=True,
        approved_at=datetime.now(timezone.utc),
    )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Staff account could not be created; check the details and retry",
        )

    db.refresh(user)
    return user


@router.get("/staff", response_model=list[UserRead])
def list_staff_accounts(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    query = (
        select(User)
        .where(User.role.in_([UserRole.TREASURER, UserRole.SECRETARY]))
        .order_by(User.created_at.desc())
    )
    return list(db.scalars(query).all())


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if user.status == AccountStatus.PENDING:
        raise HTTPException(
            status_code=403,
            detail="Your registration is awaiting administrator approval",
        )

    if user.status != AccountStatus.APPROVED or not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="This account is not permitted to sign in",
        )

    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from the current password")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully. Please sign in again on your other devices."}


@router.get("/registrations/pending", response_model=list[UserRead])
def pending_registrations(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    return list(
        db.scalars(
            select(User)
            .where(User.status == AccountStatus.PENDING)
            .order_by(User.created_at)
        ).all()
    )


@router.patch("/registrations/{user_id}/status", response_model=UserRead)
def update_registration(
    user_id: str,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    if payload.status not in (AccountStatus.APPROVED, AccountStatus.REJECTED):
        raise HTTPException(
            status_code=400,
            detail="Only approval or rejection is allowed for a pending registration",
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Member not found")

    if user.status != AccountStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail="This registration has already been reviewed",
        )

    user.status = payload.status
    if payload.status == AccountStatus.APPROVED:
        user.approved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(user)
    return user
