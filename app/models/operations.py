import enum, uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class PaymentMethod(str, enum.Enum):
    CASH = 'cash'
    BANK = 'bank'
    MOBILE = 'mobile'

class Meeting(Base):
    __tablename__ = 'meetings'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(180))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class Attendance(Base):
    __tablename__ = 'attendance'
    __table_args__ = (UniqueConstraint('meeting_id', 'member_id', name='uq_meeting_member_attendance'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True)
    member_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    marked_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default='present', nullable=False)
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class Contribution(Base):
    __tablename__ = 'contributions'
    __table_args__ = (UniqueConstraint('member_id', 'period', name='uq_member_contribution_period'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    amount_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(240))
    created_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class Payment(Base):
    __tablename__ = 'payments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contribution_id: Mapped[str] = mapped_column(ForeignKey('contributions.id'), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name='payment_method'), nullable=False)
    receipt_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    reference: Mapped[str | None] = mapped_column(String(120))
    received_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
