# app/repositories/data_management_table_repository.py
import io
import os
from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select
from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException

from app.models.data_management_table import DataManagementTable, TableStatus
from dotenv import load_dotenv
from sqlmodel import Session, select, create_engine, or_

# Load environment variables from .env file
load_dotenv()

class DataManagementTableRepository:
    def __init__(self):
        
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")

        # Construct the database URL
        self.database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        self.engine = create_engine(
            self.database_url,
            echo=True  # Set to False in production
        )
        
        # Create tables
        DataManagementTable.metadata.create_all(self.engine)
        TableStatus.metadata.create_all(self.engine)
        
        self.db = Session(self.engine)
        
        # Initialize MinIO client
        self.minio_client = Minio(
            "localhost:9000",
            access_key="BVxA5YuSF5vkzXkXMym7",
            secret_key="jLDOAIEsfef50DK90gIPb5ucON7K1WuC93dOKa8F",
            secure=False  # True for HTTPS
        )
        self.bucket_name = "customer-document-storage"
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize MinIO bucket: {str(e)}"
            )

    def create_data_management_table(
        self, data_management_table: DataManagementTable
    ) -> DataManagementTable:
        self.db.add(data_management_table)
        self.db.commit()
        self.db.refresh(data_management_table)
        return data_management_table

    def get_data_management_tables(self) -> List[DataManagementTable]:
        statement = select(DataManagementTable)
        return self.db.exec(statement).all()

    def get_data_management_table(self, table_id: int) -> Optional[DataManagementTable]:
        statement = select(DataManagementTable).where(DataManagementTable.id == table_id)
        return self.db.exec(statement).first()

    def update_data_management_table(
        self, table_id: int, data_management_table: DataManagementTable
    ) -> Optional[DataManagementTable]:
        db_table = self.get_data_management_table(table_id)
        if not db_table:
            return None
        
        table_data = data_management_table.model_dump(exclude_unset=True)
        table_data["updated_at"] = datetime.utcnow()
        
        for key, value in table_data.items():
            setattr(db_table, key, value)
        
        self.db.add(db_table)
        self.db.commit()
        self.db.refresh(db_table)
        return db_table

    def delete_data_management_table(self, table_id: int) -> Optional[DataManagementTable]:
        db_table = self.get_data_management_table(table_id)
        if db_table:
            self.db.delete(db_table)
            self.db.commit()
        return db_table

class TableStatusRepository:
    def __init__(self):
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")

        # Construct the database URL
        self.database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        self.engine = create_engine(
            self.database_url,
            echo=True  # Set to False in production
        )
        
        # Create tables
        DataManagementTable.metadata.create_all(self.engine)
        TableStatus.metadata.create_all(self.engine)
        
        self.db = Session(self.engine)
        
        # Initialize MinIO client
        self.minio_client = Minio(
            "localhost:9000",
            access_key="BVxA5YuSF5vkzXkXMym7",
            secret_key="jLDOAIEsfef50DK90gIPb5ucON7K1WuC93dOKa8F",
            secure=False  # True for HTTPS
        )
        self.bucket_name = "customer-document-storage"
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize MinIO bucket: {str(e)}"
            )

    def upload_file_table_status_for_rag(
        self, file_content: bytes, table_status: TableStatus
    ) -> TableStatus:
        current_month_date = datetime.now().strftime("%Y-%m")
        object_name = f'{current_month_date}/{table_status.filename}'
        
        try:
            # Upload file to MinIO
            self.minio_client.put_object(
                self.bucket_name,
                object_name,
                io.BytesIO(file_content),
                len(file_content)
            )
            
            # Set the file download link
            table_status.file_download_link = f'minio://{self.bucket_name}/{object_name}'
            
            # Save to database
            self.db.add(table_status)
            self.db.commit()
            self.db.refresh(table_status)
            
            return table_status
            
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to MinIO: {str(e)}"
            )

    def upload_file_table_status(self, upload_df, table_status: TableStatus) -> TableStatus:
        current_month_date = datetime.now().strftime("%Y-%m")
        object_name = f'{current_month_date}/{table_status.filename}'
        
        try:
            # Convert DataFrame to CSV in memory
            csv_buffer = io.StringIO()
            upload_df.to_csv(csv_buffer, index=False, header=True)
            csv_bytes = csv_buffer.getvalue().encode('utf-8')
            
            # Upload to MinIO
            self.minio_client.put_object(
                self.bucket_name,
                object_name,
                io.BytesIO(csv_bytes),
                len(csv_bytes)
            )
            
            table_status.file_download_link = f'minio://{self.bucket_name}/{object_name}'
            
            # Save to database
            self.db.add(table_status)
            self.db.commit()
            self.db.refresh(table_status)
            
            return table_status
            
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to MinIO: {str(e)}"
            )

    def is_month_data_approved(self, table_id: int, month_year: str) -> bool:
        statement = select(TableStatus).where(
            TableStatus.data_management_table_id == table_id,
            TableStatus.month_year == month_year
        )
        result = self.db.exec(statement).first()
        
        if result is None:
            return False
        elif not result.approved:
            self.delete_table_status(result.id)
            
        return result.approved

    def get_all_table_status(self) -> List[TableStatus]:
        statement = select(TableStatus)
        return self.db.exec(statement).all()

    def get_table_status_by_id(self, status_id: int) -> Optional[TableStatus]:
        statement = select(TableStatus).where(TableStatus.id == status_id)
        return self.db.exec(statement).first()

    def update_approval_status(
        self, status_id: int, new_approval_status: bool
    ) -> Optional[TableStatus]:
        table_status = self.get_table_status_by_id(status_id)
        if table_status:
            table_status.approved = new_approval_status
            table_status.updated_at = datetime.utcnow()
            self.db.add(table_status)
            self.db.commit()
            self.db.refresh(table_status)
        return table_status

    def download_files_by_month_year(
        self, data_management_table_id: int, month_years: List[str]
    ) -> io.BytesIO:
        combined_content = io.BytesIO()
        
        for month_year in month_years:
            file_record = self.get_file_record(data_management_table_id, month_year)
            if not file_record:
                raise HTTPException(
                    status_code=404,
                    detail=f"No file found for table {data_management_table_id} and month {month_year}."
                )

            try:
                # Extract object name from file_download_link
                object_name = file_record.file_download_link.split('/')[-2:]
                object_name = '/'.join(object_name)
                
                # Download from MinIO
                data = self.minio_client.get_object(
                    self.bucket_name,
                    object_name
                )
                combined_content.write(data.read())
                
            except S3Error as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to download file from MinIO: {str(e)}"
                )

        combined_content.seek(0)
        return combined_content

    def get_file_record(
        self, data_management_table_id: int, month_year: str
    ) -> Optional[TableStatus]:
        statement = select(TableStatus).where(
            TableStatus.data_management_table_id == data_management_table_id,
            TableStatus.month_year == month_year
        )
        return self.db.exec(statement).first()

    def delete_table_status(self, status_id: int) -> Optional[TableStatus]:
        table_status = self.get_table_status_by_id(status_id)
        if table_status:
            if table_status.file_download_link:
                try:
                    # Extract object name from file_download_link
                    object_name = table_status.file_download_link.split('/')[-2:]
                    object_name = '/'.join(object_name)
                    
                    # Delete from MinIO
                    self.minio_client.remove_object(self.bucket_name, object_name)
                except S3Error:
                    # Log error but continue with database deletion
                    pass
                    
            self.db.delete(table_status)
            self.db.commit()
            
        return table_status

    def get_table_statuses_for_data_table(
        self, data_table_id: int
    ) -> List[TableStatus]:
        statement = select(TableStatus).where(
            TableStatus.data_management_table_id == data_table_id
        )
        return self.db.exec(statement).all()

    def get_board_id_for_table_status_id(
        self, data_management_table_id: int
    ) -> Optional[int]:
        statement = select(DataManagementTable.board_id).where(
            DataManagementTable.id == data_management_table_id
        )
        result = self.db.exec(statement).first()
        return result if result else None