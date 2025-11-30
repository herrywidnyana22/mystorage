import os, uuid, shutil, datetime
from fastapi import APIRouter, UploadFile, File as FastAPIFile, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr
from ..db import get_session
from ..auth.jwt_handler import require_auth as old_require_auth  # if you still use old one elsewhere
from ..models import File as FileModel
from ..utils.response import success, error
from ..utils.auth_utils import require_auth

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ShareUserPayload(BaseModel):
    email: EmailStr
    mode: str  # "share" or "unshare"

class RenamePayload(BaseModel):
    name: str

# UPLOAD
@router.post("/upload")
def upload_file(
    upload: UploadFile = FastAPIFile(...),
    user = Depends(require_auth),
    session: Session = Depends(get_session)
):
    user_dir = os.path.join(UPLOAD_DIR, user.accountId)
    os.makedirs(user_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4()}-{upload.filename}"
    path = os.path.join(user_dir, unique_name)

    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)

    url = f"/uploads/{user.accountId}/{unique_name}"
    now = datetime.datetime.now(datetime.timezone.utc)
    ext = os.path.splitext(upload.filename)[1].lstrip(".")
    size = os.path.getsize(path)

    new_file = FileModel(
        id=str(uuid.uuid4()),
        name=upload.filename,
        url=url,
        type=upload.content_type or "application/octet-stream",
        bucketFileId=unique_name,
        accountId=user.accountId,
        extension=ext,
        size=size,
        createdAt=now,
        updatedAt=now,
        owner_id=user.id,
        users=[] if getattr(FileModel, "users", None) is None else getattr(FileModel, "users", [])
    )

    session.add(new_file)
    session.commit()
    session.refresh(new_file)

    return success(data=new_file, message="File uploaded", code=201)

# LIST
@router.get("/")
def list_files(session: Session = Depends(get_session), user = Depends(require_auth)):
    files = session.exec(select(FileModel).where(FileModel.accountId == user.accountId)).all()
    return success(data={"documents": files, "total": len(files)}, message="OK", code=200)

# DELETE
@router.delete("/{file_id}")
def delete_file(file_id: str, user = Depends(require_auth), session: Session = Depends(get_session)):
    file_obj = session.exec(select(FileModel).where(FileModel.id == file_id)).first()
    if not file_obj:
        return error("File not found", 404, {"code": "FILE_NOT_FOUND"})

    if file_obj.owner_id != user.id:
        return error("Not authorized", 403, {"code": "NOT_AUTHORIZED"})

    file_path = os.path.join("uploads", file_obj.accountId, file_obj.bucketFileId)
    if os.path.exists(file_path):
        os.remove(file_path)

    session.delete(file_obj)
    session.commit()
    return success(message="File deleted successfully", code=200)

# RENAME
@router.put("/rename/{file_id}")
def rename_file(file_id: str, payload: RenamePayload, user = Depends(require_auth), session: Session = Depends(get_session)):
    file_obj = session.get(FileModel, file_id)
    if not file_obj:
        return error("File not found", 404, {"code": "FILE_NOT_FOUND"})

    if file_obj.owner_id != user.id:
        return error("Not allowed", 403, {"code": "NOT_AUTHORIZED"})

    new_name = payload.name.strip()
    if not new_name:
        return error("Invalid name", 400, {"code": "INVALID_NAME"})

    file_obj.name = new_name
    file_obj.updatedAt = datetime.datetime.now(datetime.timezone.utc)

    session.add(file_obj)
    session.commit()
    session.refresh(file_obj)

    return success(data={"file": file_obj}, message="File renamed", code=200)

# SHARE PUBLIC (generate)
@router.post("/share/{file_id}/public")
def public_share_link(file_id: str, user = Depends(require_auth), session: Session = Depends(get_session)):
    file = session.get(FileModel, file_id)
    if not file:
        return error("File not found", 404, {"code": "FILE_NOT_FOUND"})
    if file.owner_id != user.id:
        return error("Not allowed", 403, {"code": "NOT_AUTHORIZED"})

    if not getattr(file, "shareToken", None):
        file.shareToken = uuid.uuid4().hex
        file.updatedAt = datetime.datetime.now(datetime.timezone.utc)
        session.add(file)
        session.commit()
        session.refresh(file)

    return success(data={"token": file.shareToken, "shareUrl": f"{os.getenv('APP_URL')}/files/public/{file.shareToken}"}, message="Public link generated", code=200)

# DISABLE PUBLIC LINK
@router.post("/share/{file_id}/disable")
def disable_public_link(file_id: str, user = Depends(require_auth), session: Session = Depends(get_session)):
    file = session.get(FileModel, file_id)
    if not file:
        return error("File not found", 404, {"code": "FILE_NOT_FOUND"})
    if file.owner_id != user.id:
        return error("Not allowed", 403, {"code": "NOT_AUTHORIZED"})

    file.shareToken = None
    file.updatedAt = datetime.datetime.now(datetime.timezone.utc)
    session.add(file)
    session.commit()

    return success(message="Public link disabled", code=200)

# PUBLIC ACCESS
@router.get("/public/{token}")
def public_access(token: str, session: Session = Depends(get_session)):
    file = session.exec(select(FileModel).where(FileModel.shareToken == token)).first()
    if not file:
        return error("Invalid or expired link", 404, {"code": "INVALID_TOKEN"})

    return success(data={"name": file.name, "url": file.url, "type": file.type, "size": file.size}, message="OK", code=200)

# SHARE TO USER (email)
@router.post("/share-user/{file_id}")
def share_file_to_user(file_id: str, payload: ShareUserPayload, user = Depends(require_auth), session: Session = Depends(get_session)):
    file_obj = session.get(FileModel, file_id)
    if not file_obj:
        return error("File not found", 404, {"code": "FILE_NOT_FOUND"})
    if file_obj.owner_id != user.id:
        return error("Not allowed", 403, {"code": "NOT_AUTHORIZED"})

    email = payload.email.lower().strip()
    users_list = file_obj.users or []

    if payload.mode == "share":
        if email not in [e.lower() for e in users_list]:
            users_list.append(email)
    elif payload.mode == "unshare":
        users_list = [e for e in users_list if e.lower() != email]
    else:
        return error("Invalid mode", 400, {"code": "INVALID_MODE"})

    file_obj.users = users_list
    file_obj.updatedAt = datetime.datetime.now(datetime.timezone.utc)
    session.add(file_obj)
    session.commit()
    session.refresh(file_obj)

    return success(data={"users": file_obj.users}, message="File share updated", code=200)

# CHECK ACCESS
@router.get("/access/{file_id}")
def check_access(file_id: str, user = Depends(require_auth), session: Session = Depends(get_session)):
    file_obj = session.get(FileModel, file_id)
    if not file_obj:
        return error("File not found", 404, {"code": "FILE_NOT_FOUND"})

    if file_obj.owner_id == user.id:
        return success(data={"access": True, "role": "owner"}, message="OK", code=200)

    if user.email and user.email.lower() in [e.lower() for e in (file_obj.users or [])]:
        return success(data={"access": True, "role": "shared-user"}, message="OK", code=200)

    return error("Access denied", 403, {"code": "ACCESS_DENIED"})

# DOWNLOAD
@router.get("/download/{file_id}")
def download_file(file_id: str, user = Depends(require_auth), session: Session = Depends(get_session)):
    file_obj = session.get(FileModel, file_id)
    if not file_obj:
        return error("File not found", 404, {"code": "FILE_NOT_FOUND"})

    # owner or shared user
    if file_obj.owner_id != user.id and (not user.email or user.email.lower() not in [e.lower() for e in (file_obj.users or [])]):
        return error("You do not have access to this file", 403, {"code": "ACCESS_DENIED"})

    file_path = os.path.join("uploads", file_obj.accountId, file_obj.bucketFileId)
    if not os.path.exists(file_path):
        return error("File missing on server", 404, {"code": "FILE_MISSING"})

    # Return actual file stream (FileResponse)
    return FileResponse(
        file_path,
        media_type=file_obj.type,
        filename=file_obj.name,
        headers={"Content-Disposition": f'attachment; filename="{file_obj.name}"'}
    )

# USAGE SUMMARY
@router.get("/usage")
def file_usage(user = Depends(require_auth), session: Session = Depends(get_session)):
    files = session.exec(select(FileModel).where(FileModel.accountId == user.accountId)).all()

    summary = {
        "document": {"size": 0, "latestDate": None},
        "image": {"size": 0, "latestDate": None},
        "video": {"size": 0, "latestDate": None},
        "audio": {"size": 0, "latestDate": None},
        "other": {"size": 0, "latestDate": None},
        "used": 0,
    }

    for f in files:
        size = f.size or 0
        summary["used"] += size

        file_category = (f.type.split("/")[0] if f.type else "other").lower()
        if file_category not in summary:
            file_category = "other"

        summary[file_category]["size"] += size

        created = None
        if getattr(f, "createdAt", None):
            created = f.createdAt.isoformat() if hasattr(f.createdAt, "isoformat") else str(f.createdAt)
        if created:
            if summary[file_category]["latestDate"] is None or created > summary[file_category]["latestDate"]:
                summary[file_category]["latestDate"] = created

    return success(data=summary, message="OK", code=200)
