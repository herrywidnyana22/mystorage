from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
import datetime
from sqlalchemy import Column, ARRAY, String, JSON

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[str] = Field(default=None, primary_key=True)
    fullName: str
    email: str = Field(index=True)
    avatar: Optional[str] = None
    accountId: str = Field(index=True)
    createdAt: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updatedAt: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    files: List["File"] = Relationship(back_populates="owner")


class File(SQLModel, table=True):
    __tablename__ = "files"

    id: Optional[str] = Field(default=None, primary_key=True)
    name: str
    url: str
    type: str
    bucketFileId: str = Field(index=True)
    accountId: str = Field(index=True)

    extension: Optional[str] = None
    size: Optional[int] = None

    users: List[str] = Field(default_factory=list, sa_column=Column(JSON))

    # ⬇⬇ ADD THIS
    shareToken: Optional[str] = Field(
        default=None, sa_column=Column(String, unique=True, index=True)
    )

    createdAt: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updatedAt: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    owner_id: Optional[str] = Field(default=None, foreign_key="users.id")
    owner: Optional[User] = Relationship(back_populates="files")


class SessionModel(SQLModel, table=True):
    __tablename__ = "sessions"

    id: Optional[str] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    token: str
    expires_at: datetime.datetime
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class OTP(SQLModel, table=True):
    __tablename__ = "otp"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    code: str
    expires_at: datetime.datetime
