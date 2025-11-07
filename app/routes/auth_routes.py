from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db, engine
from app.models import User, Base
from app.schemas import UserCreate, LoginRequest, TokenResponse, UserOut
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.config import settings


router = APIRouter(prefix="/api", tags=["auth"])


@router.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@router.post("/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

    token = create_access_token({"sub": str(user.id)})
    bearer = f"Bearer {token}"
    # Set httpOnly cookie for web usage
    response.set_cookie(
        key="access_token",
        value=bearer,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/bootstrap-admin")
def bootstrap_admin(db: Session = Depends(get_db)):
    # Create an admin user if not exists, using env credentials
    admin = db.query(User).filter(User.email == settings.bootstrap_admin_email).first()
    if admin:
        return {"message": "管理员已存在"}
    admin = User(
        email=settings.bootstrap_admin_email,
        hashed_password=get_password_hash(settings.bootstrap_admin_password),
        is_active=True,
        is_admin=True,
    )
    db.add(admin)
    db.commit()
    return {"message": "管理员已创建"}