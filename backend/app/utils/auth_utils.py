# app/utils/auth_utils.py
from fastapi import Request, HTTPException, Depends
from sqlmodel import Session, select
from typing import Tuple, Optional
import datetime

from ..db import get_session
from ..models import SessionModel, User
from .response import error

def get_user_from_cookie(request: Request, db: Session) -> Tuple[Optional[User], Optional[dict]]:
    token = request.cookies.get("session")
    if not token:
        return None, error("Not authenticated", 401, {"code": "AUTH_REQUIRED"})

    sess = db.exec(select(SessionModel).where(SessionModel.id == token)).first()

    if not sess:
        return None, error("Invalid session", 401, {"code": "INVALID_SESSION"})

    if sess.expires_at < datetime.datetime.now(datetime.timezone.utc):
        return None, error("Session expired", 401, {"code": "SESSION_EXPIRED"})

    user = db.exec(select(User).where(User.id == sess.user_id)).first()
    if not user:
        return None, error("User not found", 404, {"code": "USER_NOT_FOUND"})

    return user, None

def require_auth(request: Request, db: Session = Depends(get_session)) -> User:
    user, err = get_user_from_cookie(request, db)
    if err:
        # Raise HTTPException with the error dict in detail → frontend will receive consistent payload
        raise HTTPException(status_code=err.get("code", 401), detail=err)
    return user
