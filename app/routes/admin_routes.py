from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import csv
import io

from app.auth import require_admin, get_password_hash
from app.database import get_db
from app.models import User, LoginEvent


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
    # 获取每个用户最近一次登录时间
    rows = db.query(LoginEvent.user_id, func.max(LoginEvent.created_at)).group_by(LoginEvent.user_id).all()
    last_logins = {uid: ts for uid, ts in rows}
    return templates.TemplateResponse(
        "admin/users_list.html",
        {"request": request, "users": users, "title": "用户管理", "last_logins": last_logins},
    )


@router.get("/admin/users/{user_id}")
def user_detail(
    request: Request,
    user_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    start: str | None = None,
    end: str | None = None,
    ip: str | None = None,
    page: int = 1,
    size: int = 20,
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    def parse_dt(s: str | None) -> datetime | None:
        if not s:
            return None
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    start_dt = parse_dt(start)
    end_dt = parse_dt(end)

    # sanitize pagination
    page = max(1, int(page))
    size = max(5, min(100, int(size)))

    base_q = db.query(LoginEvent).filter(LoginEvent.user_id == user_id)
    if start_dt:
        base_q = base_q.filter(LoginEvent.created_at >= start_dt)
    if end_dt:
        base_q = base_q.filter(LoginEvent.created_at <= end_dt)
    if ip:
        base_q = base_q.filter(LoginEvent.ip.like(f"%{ip}%"))

    total = base_q.count()
    total_pages = max(1, (total + size - 1) // size)
    offset = (page - 1) * size
    events = base_q.order_by(LoginEvent.created_at.desc()).offset(offset).limit(size).all()

    # build query string base for pagination links
    params: list[str] = []
    if start:
        params.append(f"start={start}")
    if end:
        params.append(f"end={end}")
    if ip:
        params.append(f"ip={ip}")
    params.append(f"size={size}")
    qs_base = "&".join(params)

    def fmt_dt_for_input(dt: datetime | None) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M") if dt else ""

    return templates.TemplateResponse(
        "admin/user_detail.html",
        {
            "request": request,
            "title": f"用户详情 #{user.id}",
            "user": user,
            "events": events,
            "page": page,
            "size": size,
            "total": total,
            "total_pages": total_pages,
            "ip_kw": ip or "",
            "start_input": fmt_dt_for_input(start_dt),
            "end_input": fmt_dt_for_input(end_dt),
            "qs_base": qs_base,
        },
    )


@router.get("/admin/users/{user_id}/login-history.csv")
def export_login_history_csv(
    user_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    start: str | None = None,
    end: str | None = None,
    ip: str | None = None,
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    def parse_dt(s: str | None) -> datetime | None:
        if not s:
            return None
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    start_dt = parse_dt(start)
    end_dt = parse_dt(end)

    base_q = db.query(LoginEvent).filter(LoginEvent.user_id == user_id)
    if start_dt:
        base_q = base_q.filter(LoginEvent.created_at >= start_dt)
    if end_dt:
        base_q = base_q.filter(LoginEvent.created_at <= end_dt)
    if ip:
        base_q = base_q.filter(LoginEvent.ip.like(f"%{ip}%"))
    events = base_q.order_by(LoginEvent.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_id", "created_at", "ip", "user_agent", "success"])
    for e in events:
        writer.writerow([e.id, e.user_id, e.created_at, e.ip or "", e.user_agent or "", int(bool(e.success))])
    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=login_history_{user_id}.csv"},
    )


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