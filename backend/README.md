FastAPI Backend scaffold for MyDrive (Auth + Google Login + OTP)

How to use:
1. Copy .env.example -> .env and fill your values.
2. Create a python virtualenv:
   python3 -m venv venv
   source venv/bin/activate
3. Install dependencies:
   pip install -r requirements.txt
4. Run the server:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
5. Open docs at http://localhost:8000/docs

Notes:
- This scaffold uses SQLite by default (DATABASE_URL in .env).
- OTP emails use SMTP settings; for Gmail use App Passwords.
- Google login expects the frontend to send an ID token to /auth/google/verify.
