from fastapi import APIRouter, Depends
from ..auth.jwt_handler import require_auth
from ..utils.response import success, error

router = APIRouter()

@router.get("/me")
def me(user = Depends(require_auth)):
    if not user:
        return error(
            message="Not authenticated",
            code=401,
            error_code="NOT_AUTHENTICATED"
        )

    return success(
        message="User fetched successfully",
        data={
            "id": user.id,
            "fullName": user.fullName,
            "email": user.email,
            "avatar": user.avatar,
            "accountId": user.accountId
        }
    )
