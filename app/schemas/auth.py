
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.user import UserRole, AccountStatus


class RegistrationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=32)
    password: str = Field(min_length=10, max_length=128)


class StaffAccountCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=32)
    password: str = Field(min_length=10, max_length=128)
    role: Literal["treasurer", "secretary"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    member_id: str
    full_name: str
    email: EmailStr
    phone: str
    role: UserRole
    status: AccountStatus
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class StatusUpdate(BaseModel):
    status: AccountStatus
