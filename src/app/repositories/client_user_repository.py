# app/repositories/client_users_repository.py
from datetime import datetime, timedelta
from typing import Any, List, Optional
from sqlmodel import Session, select, create_engine, or_
from fastapi import HTTPException
import secrets
import string
import requests
from ..models.client_user import ClientUser, OTP
import requests
from typing import Any
from datetime import datetime, timedelta  
from jose import jwt
import random
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def send_sms(phone_number, otp):
    url = f'http://chotasandesh.com:9123/CsRestApi/gbt/submit-tsms?username=on2vga&password=JKRS4BW0CVK&from=ON2VGA&msisdn={phone_number}&msg=Dear+User%2C+OTP+is+{otp}+for+your+login+to+GBusiness+AI+agent+https%3A%2F%2Fvm.ltd%2FON2VGA%2F0vlBAn.%0ADo+not+share+OTP+with+anyone%2C+we+never+contact+you+to+verify+OTP.%0AFor+any+issues%2C+contact+ONEVEGA+Systems+Pvt+Ltd.&response=text'
    
    # Send the GET request
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        print("SMS sent successfully.")
    else:
        print("Failed to send SMS.")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

    
class ClientUsersRepository:
    def __init__(self):
        # Get the values from the environment
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")

        # Construct the database URL
        self.database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Create engine with the URL
        self.engine = create_engine(
            self.database_url,
            echo=True  # Set to False in production
        )        
        # Create tables
        ClientUser.metadata.create_all(self.engine)
        OTP.metadata.create_all(self.engine)

    def _generate_otp(self, length: int = 6) -> str:
        return random.randint(100000, 999999)

    def create_user(self, user: ClientUser) -> Any:
        with Session(self.engine) as session:
            db_user = user
            session.add(db_user)
            try:
                session.commit()
                session.refresh(db_user)
                return db_user
            except Exception as e:
                session.rollback()
                raise HTTPException(status_code=400, detail=str(e))

    def get_users(self) -> List[ClientUser]:
        with Session(self.engine) as session:
            statement = select(ClientUser)
            return session.exec(statement).all()

    def get_user(self, user_id: int) -> Optional[ClientUser]:
        with Session(self.engine) as session:
            statement = select(ClientUser).where(ClientUser.id == user_id)
            user = session.exec(statement).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return user

    def update_user(self, user_id: int, user: ClientUser) -> Any:
        with Session(self.engine) as session:
            db_user = session.get(ClientUser, user_id)
            if not db_user:
                raise HTTPException(status_code=404, detail="User not found")
            
            user_data = user.dict(exclude_unset=True)
            user_data["updated_at"] = datetime.utcnow()
            
            for key, value in user_data.items():
                setattr(db_user, key, value)
            
            try:
                session.add(db_user)
                session.commit()
                session.refresh(db_user)
                return db_user
            except Exception as e:
                session.rollback()
                raise HTTPException(status_code=400, detail=str(e))

    def delete_user(self, user_id: int) -> Any:
        with Session(self.engine) as session:
            user = session.get(ClientUser, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            session.delete(user)
            session.commit()
            return user

    def login_user(self, user_data: ClientUser) -> Any:
        with Session(self.engine) as session:
            statement = select(ClientUser).where(
                ClientUser.email == user_data.email,
                ClientUser.password == user_data.password
            )
            user = session.exec(statement).first()
            if not user:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            return user

    def store_otp(self, identifier: str, is_email: bool = False) -> str:
        otp = self._generate_otp()
        with Session(self.engine) as session:
            # Delete any existing OTP for this identifier
            statement = select(OTP).where(
                OTP.email == identifier if is_email else OTP.phone_number == identifier
            )
            existing_otp = session.exec(statement).first()
            if existing_otp:
                session.delete(existing_otp)
            
            # Create new OTP
            new_otp = OTP(
                phone_number=None if is_email else identifier,
                email=identifier if is_email else None,
                otp=otp,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=10)
            )
            session.add(new_otp)
            session.commit()

            # Send OTP via appropriate channel
            # if is_email:
            #     self.send_email(identifier, otp)
            # else:
            send_sms(identifier, otp)

            return otp

    def validate_otp(self, identifier: str, otp: str, is_email: bool = False) -> bool:
        with Session(self.engine) as session:
            statement = select(OTP).where(
                OTP.email == identifier if is_email else OTP.phone_number == identifier,
                OTP.otp == otp,
                OTP.expires_at > datetime.utcnow()
            )
            db_otp = session.exec(statement).first()
            
            if db_otp:
                # session.delete(db_otp)
                # session.commit()
                return True
            return False

    def delete_otp(self, identifier: str, is_email: bool = False):
        with Session(self.engine) as session:
            statement = select(OTP).where(
                OTP.email == identifier if is_email else OTP.phone_number == identifier
            )
            db_otp = session.exec(statement).first()
            if db_otp:
                session.delete(db_otp)
                session.commit()

    def get_user_by_phone(self, phone_number: str) -> Optional[ClientUser]:
        with Session(self.engine) as session:
            statement = select(ClientUser).where(ClientUser.customer_number == phone_number)
            return session.exec(statement).first()

    def get_user_by_email(self, email: str) -> Optional[ClientUser]:
        with Session(self.engine) as session:
            statement = select(ClientUser).where(ClientUser.email == email)
            return session.exec(statement).first()