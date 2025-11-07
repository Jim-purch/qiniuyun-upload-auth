from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from qiniu import Auth

from app.auth import get_current_user
from app.config import settings
from app.schemas import UploadTokenRequest


router = APIRouter(prefix="/api", tags=["qiniu"])


@router.get("/upload-token")
def get_upload_token(
    key: Optional[str] = Query(None, description="指定上传文件名，可选"),
    expires: int = Query(3600, description="上传凭证有效期(秒)"),
    _: object = Depends(get_current_user),
):
    if not settings.qiniu_access_key or not settings.qiniu_secret_key or not settings.qiniu_bucket:
        raise HTTPException(status_code=500, detail="未配置Qiniu AK/SK或Bucket")

    q = Auth(settings.qiniu_access_key, settings.qiniu_secret_key)
    token = q.upload_token(settings.qiniu_bucket, key, expires)
    return {"upload_token": token, "bucket": settings.qiniu_bucket, "key": key, "expires": expires}


@router.post("/upload-token")
def post_upload_token(
    payload: UploadTokenRequest,
    _: object = Depends(get_current_user),
):
    if not settings.qiniu_access_key or not settings.qiniu_secret_key or not settings.qiniu_bucket:
        raise HTTPException(status_code=500, detail="未配置Qiniu AK/SK或Bucket")

    q = Auth(settings.qiniu_access_key, settings.qiniu_secret_key)
    policy = payload.policy or {}
    token = q.upload_token(settings.qiniu_bucket, payload.key, payload.expires, policy)
    return {
        "upload_token": token,
        "bucket": settings.qiniu_bucket,
        "key": payload.key,
        "expires": payload.expires,
        "policy": policy,
    }