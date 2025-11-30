#/auth/router.py

from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import select, Session
from ..db import get_session
from ..models import User, OTP, SessionModel
from ..schemas import RegisterIn, LoginIn, VerifyOTPIn
from ..utils.response import success, error
from ..utils.utils import send_otp_email_sendgrid, create_token
import uuid, random, datetime

router = APIRouter()

@router.post("/register")
def register(payload: RegisterIn, session: Session = Depends(get_session)):
    exists = session.exec(select(User).where(User.email == payload.email)).first()
    if exists:
        return error("Email already registered", 409, {"code": "EMAIL_EXISTS"})

    user = User(
        id=str(uuid.uuid4()),
        fullName=payload.fullname,
        email=payload.email,
        accountId=str(uuid.uuid4())
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # create OTP
    code = str(random.randint(100000, 999999))
    otp = OTP(
        user_id=user.id,
        code=code,
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
    )
    session.add(otp)
    session.commit()

    send_otp_email_sendgrid(user.email, code)

    return success(
        data={"accountId": user.id},
        message="OTP sent to email",
        code=200
    )

@router.post("/login")
def login(payload: LoginIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user:
        return error("Email not found", 404, {"code": "EMAIL_NOT_FOUND"})

    code = str(random.randint(100000, 999999))
    otp = OTP(
        user_id=user.id,
        code=code,
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
    )
    session.add(otp)
    session.commit()

    send_otp_email_sendgrid(user.email, code)

    return success(
        data={"accountId": user.id},
        message="OTP sent to email",
        code=200
    )

@router.post("/verify-otp")
def verify(payload: VerifyOTPIn, response: Response, session: Session = Depends(get_session)):
    otp = session.exec(select(OTP).where(
        OTP.user_id == payload.accountId,
        OTP.code == payload.passcode
    )).first()

    if not otp or otp.expires_at < datetime.datetime.now(datetime.timezone.utc):
        return error("Invalid OTP", 400, {"code": "INVALID_OTP"})

    session_id = str(uuid.uuid4())
    jwt = create_token(payload.accountId)
    # Save session record
    sess = SessionModel(
        id=session_id,
        user_id=payload.accountId,
        token=jwt,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    )
    session.add(sess)
    session.commit()

    # set cookie
    response.set_cookie(
        key="session",
        value=session_id,
        httponly=True,
        secure=True,          
        samesite="none",       
        max_age=60 * 60 * 24 * 7,
        path="/"
    )

    return success(data={"sessionId": session_id}, message="Logged in", code=200)

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_session)):
    token = request.cookies.get("session")
    if token:
        sess = db.exec(select(SessionModel).where(SessionModel.token == token)).first()
        if sess:
            db.delete(sess)
            db.commit()

    response.delete_cookie("session", path="/")
    return success(message="Logged out successfully", code=200)
