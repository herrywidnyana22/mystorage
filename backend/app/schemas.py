from pydantic import BaseModel, EmailStr

class RegisterIn(BaseModel):
    fullname: str
    email: EmailStr

class LoginIn(BaseModel):
    email: EmailStr

class VerifyOTPIn(BaseModel):
    accountId: str
    passcode: str
