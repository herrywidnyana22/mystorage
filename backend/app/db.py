from sqlmodel import SQLModel, create_engine, Session
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL is missing in .env !")

engine = create_engine(DATABASE_URL, echo=True)  # echo=True biar kelihatan migrasi SQL

def init_db():
    from .models import User, File, SessionModel, OTP
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
