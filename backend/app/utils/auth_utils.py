from fastapi import Request
from sqlmodel import Session, select
import datetime

from ..models import User, SessionModel
from .response import success, error


def authorize(request: Request, db: Session):
    """
    Validate cookie session and return (user, None) if OK.
    Otherwise return (None, error_response)
    """

    # ambil cookie
    token = request.cookies.get("session")
    if not token:
        return None, error(
            message="Not authenticated",
            code=401,
            err={"code": "AUTH_REQUIRED"}
        )

    # cek session valid
    sess = db.exec(
        select(SessionModel).where(SessionModel.token == token)
    ).first()

    if not sess:
        return None, error(
            message="Invalid session",
            code=401,
            err={"code": "INVALID_SESSION"}
        )

    # expired?
    if sess.expires_at < datetime.datetime.now(datetime.timezone.utc):
        return None, error(
            message="Session expired",
            code=401,
            err={"code": "SESSION_EXPIRED"}
        )

    # ambil user
    user = db.exec(select(User).where(User.id == sess.user_id)).first()

    if not user:
        return None, error(
            message="User not found",
            code=404,
            err={"code": "USER_NOT_FOUND"}
        )

    return user, None
