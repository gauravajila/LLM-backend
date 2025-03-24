# app/models/client_user.py
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import SQLModel, Field
from pydantic import EmailStr
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CONSULTANT = "CONSULTANT"
    END_USER = "END_USER"

class PhoneRequestForm(SQLModel):
    phone_number: str

class EmailRequestForm(SQLModel):
    email: str

class OTPVerificationForm(SQLModel):
    phone_number: str
    otp: str

class EmailOTPVerificationForm(SQLModel):
    email: str
    otp: str

class LoginClientUser(SQLModel):
    email: str
    password: str
    
class ClientUser(SQLModel, table=True):
    __tablename__ = "ClientUsers"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None, index=True)
    username: Optional[str] = Field(default=None)
    password: str
    email: str = Field(unique=True, index=True)
    client_number: Optional[str] = Field(default=None)
    customer_number: Optional[str] = Field(default=None)
    subscription: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=UserRole.END_USER)
    customer_other_details: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "name": "Shashi Raj",
                    "username": "shashi_raj",
                    "email": "shashiraj.newproject@gmail.com",
                    "password": "admin",
                    "client_number": "001",
                    "customer_number": "9952974037",
                    "subscription": "Gold",
                    "role": "ADMIN",
                    "customer_other_details": "Other details"
                }
            ]
        }

class OTP(SQLModel, table=True):
    __tablename__ = "OTPs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: Optional[str] = Field(default=None, index=True)
    email: Optional[str] = Field(default=None, index=True)
    otp: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=10)
    )