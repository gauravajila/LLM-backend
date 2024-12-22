import requests
from typing import Any
from datetime import datetime, timedelta  
from jose import jwt
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.client_user import ClientUser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SECRET_KEY = "test_token"
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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

def send_email(email, otp):
    # Gmail SMTP configuration
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "vish.dharmapala.vega@gmail.com"  # Replace with your Gmail address
    sender_password = "PSidENTErSPo"  # Replace with your app-specific password

    # Email content
    subject = "Your OTP Code"
    body = f"""
    Hi,

    Your OTP code is: {otp}

    This code is valid for 5 minutes. Please do not share it with anyone.

    Best regards,
    OneVega
    """

    try:
        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Start TLS encryption
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())

        print(f"OTP email sent successfully to {email}")

    except Exception as e:
        print(f"Failed to send OTP email to {email}: {e}")
        raise

        
class ClientUsersRepository(BaseRepository):
    def __init__(self):
        super().__init__('ClientUsers')
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS ClientUsers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                username VARCHAR(255),
                password VARCHAR(255),
                email VARCHAR(255) UNIQUE,
                client_number VARCHAR(255),
                customer_number VARCHAR(255),
                subscription VARCHAR(255),
                role VARCHAR(255),
                customer_other_details TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                phone_number VARCHAR(255)  -- Added phone_number field
            );
        """)
        self.create_table(create_table_query)
        
        create_otp_table_query = text("""
            CREATE TABLE IF NOT EXISTS OTPs (
                phone_number VARCHAR(255) PRIMARY KEY,
                otp VARCHAR(6),
                created_at TIMESTAMP
            );
        """)
        self.create_table(create_otp_table_query)
        

    def create_user(self, user: ClientUser) -> Any:
        query = text("""
            INSERT INTO ClientUsers (name, username, password, email, client_number,
                                     customer_number, subscription, role, customer_other_details,
                                     created_at, updated_at, phone_number)
            VALUES (:name, :username, :password, :email, :client_number, :customer_number,
                    :subscription, :role, :customer_other_details, CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP, :phone_number)
            RETURNING id, name, username, password, email, client_number, customer_number,
                      subscription, role, customer_other_details, created_at, updated_at, phone_number;
        """)

        values = {
            "name": user.name,
            "username": user.username,
            "password": user.password,
            "email": user.email,
            "client_number": user.client_number,
            "customer_number": user.customer_number,
            "subscription": user.subscription,
            "role": user.role,
            "customer_other_details": user.customer_other_details,
            "phone_number": user.phone_number  # Added phone_number value
        }

        user_data_tuple = self.execute_query(query, values)
        user_instance = ClientUser(**dict(zip(ClientUser.__annotations__, user_data_tuple)))
        return user_instance

    def get_users(self) -> Any:
        query = text("""
            SELECT * FROM ClientUsers;
        """)

        user_data_list = self.execute_query_all(query)
        user_dict = [ClientUser(**dict(zip(ClientUser.__annotations__, user_data))) for user_data in user_data_list]
        return user_dict

    def get_user(self, user_id: int) -> Any:
        query = text("""
            SELECT * FROM ClientUsers WHERE id = :user_id;
        """)

        values = {"user_id": user_id}

        user_data_tuple = self.execute_query(query, values)
        user_instance = ClientUser(**dict(zip(ClientUser.__annotations__, user_data_tuple)))
        return user_instance

    def update_user(self, user_id: int, user: ClientUser) -> Any:
        query = text("""
            UPDATE ClientUsers
            SET name = :name, username = :username, password = :password,
                email = :email, client_number = :client_number,
                customer_number = :customer_number, subscription = :subscription,
                role = :role, customer_other_details = :customer_other_details,
                updated_at = CURRENT_TIMESTAMP, phone_number = :phone_number
            WHERE id = :user_id
            RETURNING id, name, username, password, email, client_number, customer_number,
                      subscription, role, customer_other_details, created_at, updated_at, phone_number;
        """)

        values = {
            "name": user.name,
            "username": user.username,
            "password": user.password,
            "email": user.email,
            "client_number": user.client_number,
            "customer_number": user.customer_number,
            "subscription": user.subscription,
            "role": user.role,
            "customer_other_details": user.customer_other_details,
            "phone_number": user.phone_number,  # Added phone_number value
            "user_id": user_id
        }

        user_data_tuple = self.execute_query(query, values)
        user_instance = ClientUser(**dict(zip(ClientUser.__annotations__, user_data_tuple)))
        return user_instance

    def delete_user(self, user_id: int) -> Any:
        query = text("""
            DELETE FROM ClientUsers WHERE id = :user_id
            RETURNING id, name, username, password, email, client_number, customer_number,
                      subscription, role, customer_other_details, created_at, updated_at, phone_number;
        """)

        values = {"user_id": user_id}

        user_data_tuple = self.execute_query(query, values)
        user_instance = ClientUser(**dict(zip(ClientUser.__annotations__, user_data_tuple)))
        return user_instance

    def login_user(self, user_data) -> Any:
        query = text("""
            SELECT * FROM ClientUsers WHERE email = :email AND password = :password;
        """)
        values = {"email": user_data.email, "password": user_data.password}
        user_data_tuple = self.execute_query(query, values)
        user_instance = ClientUser(**dict(zip(ClientUser.__annotations__, user_data_tuple)))
        return user_instance

    def store_otp(self, phone_number: str, otp: str):
        query = text("""
                INSERT INTO OTPs (phone_number, otp, created_at)
                VALUES (:phone_number, :otp, CURRENT_TIMESTAMP);
        """)
        values = {"phone_number": phone_number, "otp": str(otp)}
        self.create_table(query, values)

    def validate_otp(self, phone_number: str, otp: str) -> bool:
        query = text("""
            SELECT otp FROM OTPs WHERE phone_number = :phone_number AND otp = :otp;
        """)
        values = {"phone_number": phone_number, "otp": otp}
        result = self.execute_query(query, values)
        return bool(result)

    def delete_otp(self, phone_number: str):
        query = text("""
            DELETE FROM OTPs WHERE phone_number = :phone_number;
        """)
        values = {"phone_number": phone_number}
        self.create_table(query, values)
        
    def get_user_by_phone(self, phone_number: str) -> Any:
        query = text("""
            SELECT * FROM ClientUsers WHERE phone_number = :phone_number;
        """)
        values = {"phone_number": phone_number}
        user_data_tuple = self.execute_query(query, values)
        if user_data_tuple:
            user_instance = ClientUser(**dict(zip(ClientUser.__annotations__, user_data_tuple)))
            return user_instance
        return None
    
    
    def get_user_by_email(self, email):
        query = text("SELECT * FROM users WHERE email = :email")
        values = {"email": email}
        result = self.execute_query(query, values)
        return result[0] if result else None