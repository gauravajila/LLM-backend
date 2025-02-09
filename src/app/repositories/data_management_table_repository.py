# app/repositories/data_management_table_repository.py
import io
import os
from typing import List, Optional, Any
from datetime import datetime
from contextlib import contextmanager
from sqlmodel import Session, select, create_engine
from minio import Minio
from minio.error import S3Error
from fastapi import HTTPException
from app.models.data_management_table import DataManagementTable, TableStatus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BaseRepository:
    def __init__(self):
        # Database configuration
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = os.getenv("DB_PORT")
        self.db_name = os.getenv("DB_NAME")

        # MinIO configuration
        self.minio_host = os.getenv("MINIO_HOST", "localhost:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY")
        self.minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.bucket_name = os.getenv("MINIO_BUCKET", "customer-document-storage")

        # Initialize connections
        self._init_database()
        self._init_minio()

    def _init_database(self) -> None:
        """Initialize database connection"""
        self.database_url = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        self.engine = create_engine(
            self.database_url,
            echo=os.getenv("DB_ECHO", "false").lower() == "true"
        )
        
        # Create tables
        DataManagementTable.metadata.create_all(self.engine)
        TableStatus.metadata.create_all(self.engine)

    def _init_minio(self) -> None:
        """Initialize MinIO client"""
        self.minio_client = Minio(
            self.minio_host,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=self.minio_secure
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure MinIO bucket exists"""
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize MinIO bucket: {str(e)}"
            )

    def get_session(self) -> Session:
        """Get a new database session"""
        return Session(self.engine)

class DataManagementTableRepository(BaseRepository):
    def create_data_management_table(
        self, data_management_table: DataManagementTable
    ) -> DataManagementTable:
        """Create a new data management table"""
        session = self.get_session()
        try:
            session.add(data_management_table)
            session.commit()
            session.refresh(data_management_table)
            return data_management_table
        finally:
            session.close()

    def get_data_management_tables(self) -> List[DataManagementTable]:
        """Get all data management tables"""
        session = self.get_session()
        try:
            statement = select(DataManagementTable)
            return session.exec(statement).all()
        finally:
            session.close()

    def get_data_management_table(self, table_id: int) -> Optional[DataManagementTable]:
        """Get a specific data management table by ID"""
        session = self.get_session()
        try:
            statement = select(DataManagementTable).where(DataManagementTable.id == table_id)
            return session.exec(statement).first()
        finally:
            session.close()

    def update_data_management_table(
        self, table_id: int, data_management_table: DataManagementTable
    ) -> Optional[DataManagementTable]:
        """Update a data management table"""
        session = self.get_session()
        try:
            db_table = session.exec(
                select(DataManagementTable).where(DataManagementTable.id == table_id)
            ).first()
            
            if not db_table:
                return None
            
            table_data = data_management_table.model_dump(exclude_unset=True)
            table_data["updated_at"] = datetime.utcnow()
            
            for key, value in table_data.items():
                setattr(db_table, key, value)
            
            session.add(db_table)
            session.commit()
            session.refresh(db_table)
            
            # Create a copy of the data before closing the session
            result = DataManagementTable.model_validate(db_table)
            return result
        finally:
            session.close()

    def delete_data_management_table(self, table_id: int) -> Optional[DataManagementTable]:
        """Delete a data management table"""
        session = self.get_session()
        try:
            db_table = session.exec(
                select(DataManagementTable).where(DataManagementTable.id == table_id)
            ).first()
            
            if db_table:
                # Create a copy of the data before deletion
                result = DataManagementTable.model_validate(db_table)
                session.delete(db_table)
                session.commit()
                return result
            return None
        finally:
            session.close()

class TableStatusRepository(BaseRepository):
    def upload_file_table_status_for_rag(
        self, file_content: bytes, table_status: TableStatus
    ) -> TableStatus:
        """Upload file for RAG processing"""
        current_month_date = datetime.now().strftime("%Y-%m")
        object_name = f'{current_month_date}/{table_status.filename}'
        
        try:
            self.minio_client.put_object(
                self.bucket_name,
                object_name,
                io.BytesIO(file_content),
                len(file_content)
            )
            
            table_status.file_download_link = f'minio://{self.bucket_name}/{object_name}'
            
            session = self.get_session()
            try:
                session.add(table_status)
                session.commit()
                session.refresh(table_status)
                result = TableStatus.model_validate(table_status)
                return result
            finally:
                session.close()
                
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to MinIO: {str(e)}"
            )

    def upload_file_table_status(self, upload_df: Any, table_status: TableStatus) -> TableStatus:
        """Upload file from DataFrame"""
        current_month_date = datetime.now().strftime("%Y-%m")
        object_name = f'{current_month_date}/{table_status.filename}'
        
        try:
            csv_buffer = io.StringIO()
            upload_df.to_csv(csv_buffer, index=False, header=True)
            csv_bytes = csv_buffer.getvalue().encode('utf-8')
            
            self.minio_client.put_object(
                self.bucket_name,
                object_name,
                io.BytesIO(csv_bytes),
                len(csv_bytes)
            )
            
            table_status.file_download_link = f'minio://{self.bucket_name}/{object_name}'
            
            session = self.get_session()
            try:
                session.add(table_status)
                session.commit()
                session.refresh(table_status)
                result = TableStatus.model_validate(table_status)
                return result
            finally:
                session.close()
                
        except S3Error as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to MinIO: {str(e)}"
            )

    def is_month_data_approved(self, table_id: int, month_year: str) -> bool:
        """Check if month data is approved"""
        session = self.get_session()
        try:
            statement = select(TableStatus).where(
                TableStatus.data_management_table_id == table_id,
                TableStatus.month_year == month_year
            )
            result = session.exec(statement).first()
            
            if result is None:
                return False
            elif not result.approved:
                self.delete_table_status(result.id)
                
            return result.approved
        finally:
            session.close()

    def get_all_table_status(self) -> List[TableStatus]:
        """Get all table statuses"""
        session = self.get_session()
        try:
            statement = select(TableStatus)
            return session.exec(statement).all()
        finally:
            session.close()

    def get_table_status_by_id(self, status_id: int) -> Optional[TableStatus]:
        """Get table status by ID"""
        session = self.get_session()
        try:
            statement = select(TableStatus).where(TableStatus.id == status_id)
            return session.exec(statement).first()
        finally:
            session.close()

    def update_approval_status(
        self, status_id: int, new_approval_status: bool
    ) -> Optional[TableStatus]:
        """Update approval status"""
        session = self.get_session()
        try:
            table_status = session.exec(
                select(TableStatus).where(TableStatus.id == status_id)
            ).first()
            
            if table_status:
                table_status.approved = new_approval_status
                table_status.updated_at = datetime.utcnow()
                session.add(table_status)
                session.commit()
                session.refresh(table_status)
                result = TableStatus.model_validate(table_status)
                return result
            return None
        finally:
            session.close()

    def download_files_by_month_year(
        self, data_management_table_id: int, month_years: List[str]
    ) -> io.BytesIO:
        """Download files by month and year"""
        combined_content = io.BytesIO()
        
        for month_year in month_years:
            file_record = self.get_file_record(data_management_table_id, month_year)
            if not file_record:
                raise HTTPException(
                    status_code=404,
                    detail=f"No file found for table {data_management_table_id} and month {month_year}."
                )

            try:
                object_name = '/'.join(file_record.file_download_link.split('/')[-2:])
                data = self.minio_client.get_object(self.bucket_name, object_name)
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
        """Get file record"""
        session = self.get_session()
        try:
            statement = select(TableStatus).where(
                TableStatus.data_management_table_id == data_management_table_id,
                TableStatus.month_year == month_year
            )
            return session.exec(statement).first()
        finally:
            session.close()

    def delete_table_status(self, status_id: int) -> Optional[TableStatus]:
        """Delete table status"""
        session = self.get_session()
        try:
            table_status = session.exec(
                select(TableStatus).where(TableStatus.id == status_id)
            ).first()
            
            if table_status:
                if table_status.file_download_link:
                    try:
                        object_name = '/'.join(table_status.file_download_link.split('/')[-2:])
                        self.minio_client.remove_object(self.bucket_name, object_name)
                    except S3Error:
                        # Log error but continue with database deletion
                        pass
                
                # Create a copy of the data before deletion
                result = TableStatus.model_validate(table_status)
                session.delete(table_status)
                session.commit()
                return result
            return None
        finally:
            session.close()

    def get_table_statuses_for_data_table(
        self, data_table_id: int
    ) -> List[TableStatus]:
        """Get table statuses for data table"""
        session = self.get_session()
        try:
            statement = select(TableStatus).where(
                TableStatus.data_management_table_id == data_table_id
            )
            return session.exec(statement).all()
        finally:
            session.close()

    def get_board_id_for_table_status_id(
        self, data_management_table_id: int
    ) -> Optional[int]:
        """Get board ID for table status ID"""
        session = self.get_session()
        try:
            statement = select(DataManagementTable.board_id).where(
                DataManagementTable.id == data_management_table_id
            )
            result = session.exec(statement).first()
            return result if result else None
        finally:
            session.close()