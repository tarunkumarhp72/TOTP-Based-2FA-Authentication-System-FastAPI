from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email:EmailStr
    password:str
    
class LoginRequest(BaseModel):
    email:EmailStr
    password:str
    
class OTPVerfiy(BaseModel):
    otp:str