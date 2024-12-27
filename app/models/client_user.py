# app/models/client_user.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.main_board import MainBoard  # Import MainBoard for client-user relationship

class PhoneRequestForm(BaseModel):
    phone_number: str

class OTPVerificationForm(BaseModel):
    phone_number: str
    otp: str
    
class ClientUser(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    username: Optional[str] = None
    password: str
    email: str
    client_number: Optional[str] = None
    customer_number: Optional[str] = None
    subscription: Optional[str] = None 
    role: Optional[str] = None  # ADMIN|CONSULTANT|END_USER
    customer_other_details: Optional[str] = None  # JSON for all other details
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    phone_number: Optional[str] = None
    boards: Optional[List[MainBoard]] = []  # Added boards relationship

    class Config:
        orm_mode = True

        # Example data for documentation
        json_schema_extra = {
            "examples": [
                {
                    "name": "John Doe",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "password": "secure_password",
                    "client_number": "001",
                    "customer_number": "1234567890",
                    "subscription": "Gold",
                    "role": "Admin",
                    "customer_other_details": "Other details"
                }
            ]
        }
