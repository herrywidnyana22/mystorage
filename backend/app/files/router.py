import os, uuid, shutil, datetime
from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr

from ..db import get_session
from ..auth.jwt_handler import require_auth
from ..models import File as FileModel, User
from ..utils.response import success, error

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ShareUserPayload(BaseModel):
    email: EmailStr
    mode: str  # "share" or "unshare"

# LIST FILES
@router.get("")
@router.get("/")
def list_files(user=Depends(require_auth), session: Session = Depends(get_session)):
    files = session.exec(
        select(FileModel).where(FileModel.accountId == user.accountId)
    ).all()

    return success("File list", data={"documents": files, "total": len(files)})


# UPLOAD FILE
@router.post("/upload")
def upload_file(
    upload: UploadFile = File(...),
    user=Depends(require_auth),
    session: Session = Depends(get_session)
):
    try:
        user_dir = os.path.join(UPLOAD_DIR, user.accountId)
        os.makedirs(user_dir, exist_ok=True)

        bucket_name = f"{uuid.uuid4()}-{upload.filename}"
        path = os.path.join(user_dir, bucket_name)

        with open(path, "wb") as f:
            shutil.copyfileobj(upload.file, f)

        url = f"/uploads/{user.accountId}/{bucket_name}"
        now = datetime.datetime.now(datetime.timezone.utc)

        ext = os.path.splitext(upload.filename)[1].lstrip(".")
        size = os.path.getsize(path)

        new_file = FileModel(
            id=str(uuid.uuid4()),
            name=upload.filename,
            url=url,
            type=upload.content_type or "application/octet-stream",
            bucketFileId=bucket_name,
            accountId=user.accountId,
            extension=ext,
            size=size,
            createdAt=now,
            updatedAt=now,
            owner_id=user.id,
        )

        session.add(new_file)
        session.commit()
        session.refresh(new_file)

        return success("File uploaded", data=new_file)

    except Exception as e:
        return error("Upload failed", 500, str(e))


# DELETE FILE
@router.delete("/{file_id}")
def delete_file(
    file_id: str,
    user=Depends(require_auth),
    session: Session = Depends(get_session)
):
    file_obj = session.get(FileModel, file_id)

    if not file_obj:
        return error("File not found", 404)

    if file_obj.owner_id != user.id:
        return error("Not authorized", 403)

    file_path = os.path.join("uploads", user.accountId, file_obj.bucketFileId)
    if os.path.exists(file_path):
        os.remove(file_path)

    session.delete(file_obj)
    session.commit()

    return success("File deleted")


# RENAME FILE
class RenamePayload(BaseModel):
    name: str


@router.put("/rename/{file_id}")
def rename_file(
    file_id: str,
    payload: RenamePayload,
    user=Depends(require_auth),
    session: Session = Depends(get_session)
):
    file_obj = session.get(FileModel, file_id)

    if not file_obj:
        return error("File not found", 404)

    if file_obj.owner_id != user.id:
        return error("Not allowed", 403)

    new_name = payload.name.strip()
    if not new_name:
        return error("Invalid name", 400)

    file_obj.name = new_name
    file_obj.updatedAt = datetime.datetime.now(datetime.timezone.utc)

    session.add(file_obj)
    session.commit()
    session.refresh(file_obj)

    return success("File renamed", data=file_obj)


# PUBLIC SHARE LINK
@router.post("/share/{file_id}/public")
def public_share_link(
    file_id: str,
    user=Depends(require_auth),
    session: Session = Depends(get_session)
):
    file = session.get(FileModel, file_id)

    if not file:
        return error("File not found", 404)

    if file.owner_id != user.id:
        return error("Not allowed", 403)

    if not file.shareToken:
        file.shareToken = uuid.uuid4().hex
        file.updatedAt = datetime.datetime.now(datetime.timezone.utc)
        session.add(file)
        session.commit()

    return success("Share link generated", data={
        "token": file.shareToken,
        "shareUrl": f"{os.getenv('APP_URL')}/files/public/{file.shareToken}"
    })


# DISABLE PUBLIC LINK
@router.post("/share/{file_id}/disable")
def disable_public_link(
    file_id: str,
    user=Depends(require_auth),
    session: Session = Depends(get_session)
):
    file = session.get(FileModel, file_id)

    if not file:
        return error("File not found", 404)

    if file.owner_id != user.id:
        return error("Not allowed", 403)

    file.shareToken = None
    file.updatedAt = datetime.datetime.now(datetime.timezone.utc)
    session.add(file)
    session.commit()

    return success("Public link disabled")


# PUBLIC ACCESS
@router.get("/public/{token}")
def public_access(token: str, session: Session = Depends(get_session)):
    file = session.exec(
        select(FileModel).where(FileModel.shareToken == token)
    ).first()

    if not file:
        return error("Invalid or expired link", 404)

    return success("File available", data={
        "name": file.name,
        "url": file.url,
        "type": file.type,
        "size": file.size
    })


# SHARE WITH SPECIFIC USER (EMAIL)
@router.post("/share-user/{file_id}")
def share_file_to_user(
    file_id: str,
    payload: ShareUserPayload,
    user=Depends(require_auth),
    session: Session = Depends(get_session)
):
    file_obj = session.get(FileModel, file_id)

    if not file_obj:
        return error("File not found", 404)

    if file_obj.owner_id != user.id:
        return error("Not allowed", 403)

    email = payload.email.lower().strip()

    if payload.mode == "share":
        if email not in file_obj.users:
            file_obj.users.append(email)
    elif payload.mode == "unshare":
        file_obj.users = [e for e in file_obj.users if e != email]
    else:
        return error("Invalid mode", 400)

    file_obj.updatedAt = datetime.datetime.now(datetime.timezone.utc)
    session.add(file_obj)
    session.commit()

    return success("Share updated", data={"users": file_obj.users})


# CHECK ACCESS PERMISSION
@router.get("/access/{file_id}")
def check_access(
    file_id: str,
    user=Depends(require_auth),
    session: Session = Depends(get_session)
):
    file_obj = session.get(FileModel, file_id)

    if not file_obj:
        return error("File not found", 404)

    if file_obj.owner_id == user.id:
        return success("Access granted", data={"access": True, "role": "owner"})
