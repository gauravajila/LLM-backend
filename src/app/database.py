# app/database.py
import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session
from contextlib import contextmanager

# Load environment variables from .env file
load_dotenv()

# Get database configuration from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Construct the database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    pool_pre_ping=True,  # Enable connection pool pre-ping
    pool_size=5,  # Set the pool size
    max_overflow=10  # Set the maximum number of connections that can be created beyond pool_size
)

# Create all tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Session manager
@contextmanager
def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

# Function to verify database connection
def verify_database_connection():
    try:
        with get_session() as session:
            session.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return False

# Initialize database
def init_db():
    try:
        # create_db_and_tables()
        if verify_database_connection():
            print("Database initialized successfully")
        else:
            print("Database initialization failed")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")