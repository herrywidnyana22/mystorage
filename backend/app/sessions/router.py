from fastapi import APIRouter, Depends, Request
from sqlmodel import Session
from ..db import get_session
from ..utils.auth_utils import authorize
from ..utils.response import success

router = APIRouter()

@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_session)):
    user, err = authorize(request, db)
    if err:
        return err

    return success(
        message="Session verified",
        data={
            "id": user.id,
            "fullName": user.fullName,
            "email": user.email,
            "avatar": user.avatar,
            "accountId": user.accountId,
        }
    )
