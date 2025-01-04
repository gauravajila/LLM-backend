
import os
import random
from fastapi import APIRouter, Depends, HTTPException, status, Header, Security
from fastapi.security import APIKeyHeader
from typing import List
from datetime import timedelta
from fastapi.responses import JSONResponse
from app.models.client_user import ClientUser, LoginClientUser, PhoneRequestForm, OTPVerificationForm, EmailRequestForm, EmailOTPVerificationForm
from app.repositories.client_user_repository import ClientUsersRepository, send_sms
from app.exceptions import UserNotFoundException, EmailAlreadyInUseException, InternalServerErrorException
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

# Define API key security scheme
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def verify_token(x_token: str = Security(api_key_header)):
    if x_token != SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )

router = APIRouter(prefix="/client-users", tags=["Client Users"])

# Creating an instance of the UsersRepository
users_repository = ClientUsersRepository()

@router.post("/", response_model=ClientUser)
async def create_user(user: ClientUser, token: str = Depends(verify_token)):
    try:
        created_user = users_repository.create_user(user)
        return created_user
    except EmailAlreadyInUseException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use")
    except InternalServerErrorException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[ClientUser])
async def get_users(token: str = Depends(verify_token)):
    users = users_repository.get_users()
    return users

@router.get("/{user_id}", response_model=ClientUser)
async def get_user(user_id: int, token: str = Depends(verify_token)):
    try:
        user = users_repository.get_user(user_id)
        if not user:
            raise UserNotFoundException
        return user
    except UserNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClientUser not found")

@router.put("/{user_id}", response_model=ClientUser)
async def update_user(user_id: int, user: ClientUser, token: str = Depends(verify_token)):
    try:
        updated_user = users_repository.update_user(user_id, user)
        if not updated_user:
            raise UserNotFoundException
        return updated_user
    except EmailAlreadyInUseException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use")
    except UserNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClientUser not found")
    except InternalServerErrorException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{user_id}", response_model=dict)
async def delete_user(user_id: int, token: str = Depends(verify_token)):
    try:
        deleted_user = users_repository.delete_user(user_id)
        if not deleted_user:
            raise UserNotFoundException
        response_data = {"status_code": 200, "detail": "ClientUser deleted successfully"}
        return response_data
    except UserNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClientUser not found")
    except InternalServerErrorException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/login", response_model=dict)
def login(user_data: LoginClientUser, token: str = Depends(verify_token)):
    try:
        user = users_repository.login_user(user_data)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        response_data = {
            "user_id": user.id,
            "user_name": user.name,
            "email": user.email,
            "role": user.role,
            "subscription": user.subscription,
            "customer_other_details": user.customer_other_details,
            
            # Add other user details as needed
        }

        return JSONResponse(content=response_data)
    except HTTPException as e:
        raise e
    except InternalServerErrorException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/send-otp", response_model=dict)
async def send_otp_to_user(form_data: PhoneRequestForm, token: str = Depends(verify_token)):
    user = users_repository.get_user_by_phone(form_data.phone_number)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")

    users_repository.delete_otp(form_data.phone_number)
    otp = users_repository.store_otp(form_data.phone_number)

    return {"message": f"OTP sent successfully: {otp}"}

@router.post("/verify-otp", response_model=dict)
async def verify_otp(form_data: OTPVerificationForm, token: str = Depends(verify_token)):
    if users_repository.validate_otp(form_data.phone_number, form_data.otp):
        user = users_repository.get_user_by_phone(form_data.phone_number)
        
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        users_repository.delete_otp(form_data.phone_number)
        
        response_data = {
            "user_id": user.id,
            "user_name": user.name,
            "email": user.email,
            "role": user.role,
            "subscription": user.subscription,
            "customer_other_details": user.customer_other_details,
            # Add other user details as needed
        }
        
        return JSONResponse(content=response_data)
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid OTP"
    )
    
    
@router.post("/send-email-otp", response_model=dict)
async def send_otp_to_email(form_data: EmailRequestForm, token: str = Depends(verify_token)):
    user = users_repository.get_user_by_email(form_data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")

    users_repository.delete_otp(form_data.email)  # Use email in the phone_number column
    otp = random.randint(1000, 9999)
    users_repository.store_otp(form_data.email, otp)  # Store email as phone_number
    #send_email(form_data.email, otp)

    return {"message": "OTP sent successfully to email"}

@router.post("/verify-email-otp", response_model=dict)
async def verify_email_otp(form_data: EmailOTPVerificationForm, token: str = Depends(verify_token)):
    if users_repository.validate_otp(form_data.email, form_data.otp):  # Validate using email as phone_number
        users_repository.delete_otp(form_data.email)
        user = users_repository.get_user_by_email(form_data.email)

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        response_data = {
            "user_id": user.id,
            "user_name": user.name,
            "email": user.email,
            "role": user.role,
            "subscription": user.subscription,
            "customer_other_details": user.customer_other_details,
        }

        return JSONResponse(content=response_data)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid OTP"
    )