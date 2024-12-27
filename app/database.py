import os
import psycopg2  # Used for AWS RDS connection
from configparser import ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from google.cloud.sql.connector import Connector, IPTypes
import pg8000  # Used for Google Cloud SQL connection

# Initialize SQLAlchemy Base
Base = declarative_base()

# AWS RDS connection
def get_database_connection_aws():
    config = ConfigParser()
    config.read('app/config.ini')  # Assuming config file is in the 'app' directory
    db_config = config['database']

    conn = psycopg2.connect(
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password'],
        host=db_config['host'],
        port=db_config['port']
    )

    return conn

# Google Cloud SQL connection using Cloud SQL Connector
def get_database_connection():
    config = ConfigParser()
    config.read('app/config.ini')  # Assuming config file is in the 'app' directory
    db_config = config['database']

    db_user = db_config['user']  # e.g. 'my-database-user'
    db_pass = db_config['password']  # e.g. 'my-database-password'
    db_name = db_config['dbname']  # e.g. 'my-database'
    unix_socket_path = db_config['host']  # e.g. '/cloudsql/project:region:instance'
    ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

    # Initialize Cloud SQL Python Connector object
    connector = Connector()

    # Function to get a connection
    def getconn() -> pg8000.dbapi.Connection:
        conn: pg8000.dbapi.Connection = connector.connect(
            unix_socket_path,
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name,
            ip_type=ip_type
        )
        return conn

    # Create SQLAlchemy engine for Google Cloud SQL
    engine = create_engine(
        "postgresql+pg8000://",  # PostgreSQL URL with pg8000 driver
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,  # 30 seconds timeout
        pool_recycle=1800,  # Recycle connections every 30 minutes
    )
    return engine

# Create a sessionmaker for SQLAlchemy ORM
engine = get_database_connection()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

