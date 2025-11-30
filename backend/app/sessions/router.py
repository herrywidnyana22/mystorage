# app/sessions/router.py
from fastapi import APIRouter, Depends
from ..utils.response import success
from ..utils.auth_utils import require_auth

router = APIRouter()

@router.get("/me")
def get_me(user = Depends(require_auth)):
    return success(
        data={
            "id": user.id,
            "fullName": user.fullName,
            "email": user.email,
            "avatar": user.avatar,
            "accountId": user.accountId
        },
        message="Session verified",
        code=200
    )
