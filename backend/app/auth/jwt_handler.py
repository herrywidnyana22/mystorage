# app/auth/jwt_handler.py
from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select
from ..db import get_session
from ..models import SessionModel, User
from ..utils.utils import verify_token
import datetime

def require_auth(request: Request, db: Session = Depends(get_session)) -> User:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # verify JWT signature & payload
    try:
        payload = verify_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise Exception("Invalid token payload")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # check session record
    sess = db.exec(select(SessionModel).where(SessionModel.token == token)).first()
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid session")

    # check expiry (use timezone-aware compare)
    if sess.expires_at and sess.expires_at < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user = db.exec(select(User).where(User.id == sess.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
