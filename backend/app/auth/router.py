# app/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import select, Session
from ..db import get_session
from ..models import User, OTP, SessionModel
from ..schemas import RegisterIn, LoginIn, VerifyOTPIn
from ..utils.utils import send_otp_email_sendgrid, create_token
from ..utils.response import success, error
import uuid, random, datetime

router = APIRouter()

@router.post("/register")
def register(payload: RegisterIn, session: Session = Depends(get_session)):
    exists = session.exec(select(User).where(User.email == payload.email)).first()
    if exists:
        return error("Email already registered", code=409, err={"message": "Email already registered"})

    user = User(id=str(uuid.uuid4()), fullName=payload.fullname, email=payload.email, accountId=str(uuid.uuid4()))
    session.add(user); session.commit(); session.refresh(user)

    code = str(random.randint(100000, 999999))
    otp = OTP(user_id=user.id, code=code, expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10))
    session.add(otp); session.commit()

    send_otp_email_sendgrid(user.email, code)
    return success(data={"accountId": user.id}, message="OTP sent to email", code=200)

@router.post("/login")
def login(payload: LoginIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user:
        return error("Email not found", code=404, err={"message": "Email not found"})

    code = str(random.randint(100000, 999999))
    otp = OTP(user_id=user.id, code=code, expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10))
    session.add(otp); session.commit()

    send_otp_email_sendgrid(user.email, code)
    return success(data={"accountId": user.id}, message="OTP sent to email", code=200)

@router.post("/verify-otp")
def verify(payload: VerifyOTPIn, response: Response, session: Session = Depends(get_session)):
    otp = session.exec(select(OTP).where(
        OTP.user_id == payload.accountId,
        OTP.code == payload.passcode
    )).first()

    if not otp or otp.expires_at < datetime.datetime.now(datetime.timezone.utc):
        return error("Invalid OTP", code=400, err={"message": "Invalid OTP"})

    token = create_token(payload.accountId)

    # create a session record
    now = datetime.datetime.now(datetime.timezone.utc)
    sess = SessionModel(id=str(uuid.uuid4()), user_id=payload.accountId, token=token, created_at=now, expires_at=now + datetime.timedelta(days=7))
    session.add(sess); session.commit()

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/"
    )

    return success(data={"sessionId": token}, message="Verified", code=200)

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_session)):
    token = request.cookies.get("session")
    if token:
        sess = db.exec(select(SessionModel).where(SessionModel.token == token)).first()
        if sess:
            db.delete(sess)
            db.commit()

    # delete cookie on client
    response.delete_cookie("session", path="/")
    return success(message="Logged out successfully", code=200)
