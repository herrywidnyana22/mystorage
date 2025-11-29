# app/auth/google.py
from fastapi import APIRouter, HTTPException, Response, Depends
from sqlmodel import select, Session
import requests, os, uuid, datetime
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
        return error("id_token required", code=400)

    info = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}").json()

    # debug log (remove in prod)
    print("=========[GOOGLE DEBUG]==========")
    print("AUD :", info.get("aud"))
    print("CLIENT:", GOOGLE_CLIENT_ID)
    print("FULL :", info)
    print("=================================")

    if info.get("aud") != GOOGLE_CLIENT_ID:
        return error("Invalid Google aud", code=400)

    email = info.get("email")
    name = info.get("name", "")

    # find or create user
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        user = User(id=str(uuid.uuid4()), fullName=name, email=email, accountId=str(uuid.uuid4()))
        session.add(user)
        session.commit()
        session.refresh(user)

    # generate jwt
    jwt = create_token(user.id)

    # create server-side session record (store cookie token)
    now = datetime.datetime.now(datetime.timezone.utc)
    sess = SessionModel(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token=jwt,
        created_at=now,
        expires_at=now + datetime.timedelta(days=7)
    )
    session.add(sess)
    session.commit()

    # set cookie on the Response object that will be returned
    # path="/" is important; httponly True so JS cannot read token
    response.set_cookie(
        key="session",
        value=jwt,
        httponly=True,
        secure=False,      # set True in production with HTTPS
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/"
    )

    data = {
        "sessionId": jwt,
        "accountId": user.id,
        "email": user.email,
        "fullName": user.fullName
    }

    return success(data=data, message="Google login success", code=200)
