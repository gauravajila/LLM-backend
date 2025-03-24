import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status, Header, Security
from fastapi.security import APIKeyHeader
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