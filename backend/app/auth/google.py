#/auth/google.py

from fastapi import APIRouter, Depends, HTTPException, Response, Request
import requests, os, uuid, datetime
from sqlmodel import select, Session
from ..db import get_session
from ..models import User, SessionModel
from ..utils.utils import create_token
from ..utils.response import success, error

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

@router.post("/verify")
def google_verify(payload: dict, response: Response, session: Session = Depends(get_session)):
    id_token = payload.get("id_token")
    if not id_token:
        return error("id_token required", 400, {"code": "MISSING_TOKEN"})

    # Validate Google token
    info = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}").json()

    if info.get("aud") != GOOGLE_CLIENT_ID:
        return error("Invalid Google aud", 400, {"code": "INVALID_AUD"})

    email = info.get("email")
    name = info.get("name", "")

    # Check or create user
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            fullName=name,
            email=email,
            accountId=str(uuid.uuid4())
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    # Create token and session row
    session_id = str(uuid.uuid4())
    jwt = create_token(user.id)
    now = datetime.datetime.now(datetime.timezone.utc)
    sess = SessionModel(
        id=session_id,
        user_id=user.id,
        token=jwt,
        created_at=now,
        expires_at=now + datetime.timedelta(days=7)
    )
    session.add(sess)
    session.commit()

    # set cookie via Response
    response.set_cookie(
        key="session",
        value=session_id,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )

    return success(
        data={
            "sessionId": jwt,
            "accountId": user.id,
            "email": user.email,
            "fullName": user.fullName
        },
        message="Google login success",
        code=200
    )
