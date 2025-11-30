# app/main.py
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from .db import init_db

# routers
from .auth.google import router as google_router
from .auth.router import router as auth_router
from .users.router import router as users_router
from .files.router import router as files_router
from .sessions.router import router as sessions_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database initialized and app started.")
    yield
    print("App shutdown complete.")

app = FastAPI(title="MyDrive Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# order matters: mount google first (prefix /auth/google) then /auth
app.include_router(google_router, prefix="/auth/google", tags=["auth_google"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(files_router, prefix="/files", tags=["files"])
app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
