from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models.operations import PaymentMethod

class MemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, min_length=5, max_length=32)
    is_active: bool | None = None

class MeetingCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str | None = None
    location: str | None = Field(default=None, max_length=180)
    starts_at: datetime
class MeetingRead(MeetingCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_by: str
    created_at: datetime
class AttendanceCreate(BaseModel):
    member_id: str
    status: str = Field(default='present', pattern='^(present|absent|excused)$')
class ContributionCreate(BaseModel):
    member_id: str
    period: str = Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')
    amount_due: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=240)
class ContributionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    member_id: str
    period: str
    amount_due: Decimal
    description: str | None
class PaymentCreate(BaseModel):
    contribution_id: str
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: PaymentMethod
    reference: str | None = Field(default=None, max_length=120)
class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    contribution_id: str
    amount: Decimal
    method: PaymentMethod
    receipt_number: str
    reference: str | None
    received_by: str
    paid_at: datetime
