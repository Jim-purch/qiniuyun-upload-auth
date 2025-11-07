from pydantic import BaseModel, EmailStr
from typing import Any, Optional, Dict


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UploadTokenRequest(BaseModel):
    key: Optional[str] = None
    expires: int = 3600
    policy: Optional[Dict[str, Any]] = None