from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_admin, get_password_hash
from app.database import get_db
from app.models import User


router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/login")
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request, "title": "管理员登录"})


@router.post("/admin/login")
def admin_login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    from app.auth import verify_password, create_access_token

    if not user or not user.is_admin or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "admin/login.html", {"request": request, "error": "账号或密码错误，或非管理员"}, status_code=401
        )

    token = create_access_token({"sub": str(user.id)})
    bearer = f"Bearer {token}"
    response = RedirectResponse(url="/admin/users", status_code=302)
    response.set_cookie("access_token", bearer, httponly=True, secure=False, samesite="lax")
    return response


@router.get("/admin/users")
def list_users(request: Request, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.desc()).all()
    return templates.TemplateResponse("admin/users_list.html", {"request": request, "users": users, "title": "用户管理"})


@router.get("/admin/users/new")
def new_user_page(request: Request, _: User = Depends(require_admin)):
    return templates.TemplateResponse("admin/user_form.html", {"request": request, "title": "新增用户", "user": None})


@router.post("/admin/users/new")
def create_user(
    response: Response,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    is_admin: Optional[bool] = Form(False),
):
    exists = db.query(User).filter(User.email == email).first()
    if exists:
        raise HTTPException(status_code=400, detail="邮箱已存在")
    user = User(email=email, hashed_password=get_password_hash(password), is_active=True, is_admin=bool(is_admin))
    db.add(user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)


@router.get("/admin/users/edit/{user_id}")
def edit_user_page(request: Request, user_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return templates.TemplateResponse("admin/user_form.html", {"request": request, "title": "编辑用户", "user": user})


@router.post("/admin/users/edit/{user_id}")
def update_user(
    user_id: int,
    response: Response,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: Optional[str] = Form(None),
    is_admin: Optional[bool] = Form(False),
    is_active: Optional[bool] = Form(True),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.email = email
    user.is_admin = bool(is_admin)
    user.is_active = bool(is_active)
    if password:
        user.hashed_password = get_password_hash(password)
    db.add(user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)


@router.post("/admin/users/delete/{user_id}")
def delete_user(user_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)