
import random
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import timedelta
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from app.models.client_user import ClientUser, PhoneRequestForm, OTPVerificationForm
from app.repositories.client_user_repository import ClientUsersRepository, create_access_token, send_sms, send_email
from app.exceptions import UserNotFoundException, EmailAlreadyInUseException, InternalServerErrorException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

router = APIRouter(prefix="/client-users", tags=["Client Users"])

# Creating an instance of the UsersRepository
users_repository = ClientUsersRepository()

@router.post("/", response_model=ClientUser)
async def create_user(user: ClientUser):
    try:
        created_user = users_repository.create_user(user)
        return created_user
    except EmailAlreadyInUseException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use")
    except InternalServerErrorException as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[ClientUser])
async def get_users():
    users = users_repository.get_users()
    return users

@router.get("/{user_id}", response_model=ClientUser)
async def get_user(user_id: int):
    try:
        user = users_repository.get_user(user_id)
        if not user:
            raise UserNotFoundException
        return user
    except UserNotFoundException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClientUser not found")

@router.put("/{user_id}", response_model=ClientUser)
async def update_user(user_id: int, user: ClientUser):
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
async def delete_user(user_id: int):
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
def login(user_data: ClientUser):
    try:
        user = users_repository.login_user(user_data)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user_data.email}, expires_delta=expires_delta)

        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "user_name": user.name,
#            "name":user.name,
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
async def send_otp_to_user(form_data: PhoneRequestForm):
    user = users_repository.get_user_by_phone(form_data.phone_number)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")

    users_repository.delete_otp(form_data.phone_number)
    # Generate OTP and store it
    otp = random.randint(1000, 9999)
    users_repository.store_otp(form_data.phone_number, otp)
    send_sms(form_data.phone_number, otp)

    return {"message": "OTP sent successfully"}

@router.post("/verify-otp", response_model=dict)
async def verify_otp(form_data: OTPVerificationForm):
    if users_repository.validate_otp(form_data.phone_number, form_data.otp):
        users_repository.delete_otp(form_data.phone_number)
        user = users_repository.get_user_by_phone(form_data.phone_number)
        
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.phone_number}, expires_delta=access_token_expires
        )
        
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
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
async def send_otp_to_email(form_data: PhoneRequestForm):
    user = users_repository.get_user_by_email(form_data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")

    users_repository.delete_otp(form_data.email)  # Use email in the phone_number column
    otp = random.randint(1000, 9999)
    users_repository.store_otp(form_data.email, otp)  # Store email as phone_number
    send_email(form_data.email, otp)

    return {"message": "OTP sent successfully to email"}

@router.post("/verify-email-otp", response_model=dict)
async def verify_email_otp(form_data: OTPVerificationForm):
    if users_repository.validate_otp(form_data.email, form_data.otp):  # Validate using email as phone_number
        users_repository.delete_otp(form_data.email)
        user = users_repository.get_user_by_email(form_data.email)

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.email}, expires_delta=access_token_expires
        )

        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
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