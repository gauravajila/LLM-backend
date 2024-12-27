# The `DataManagementTableRepository` and `TableStatusRepository` classes are used to interact with
# the database tables for data management tables and table statuses, respectively.
# app/repositories/data_management_table_repository.py
import os
import io
from typing import Any, List, Optional
from sqlalchemy import text
from google.cloud import storage
#from google.cloud import pubsub_v1
from app.repositories.base_repository import BaseRepository
from app.models.data_management_table import DataManagementTable, TableStatus
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status


GCP__BUCKET = "dm_03082024"

class DataManagementTableRepository(BaseRepository):
    def __init__(self):
        super().__init__('DataManagementTable')  # Corrected table name
        create_table_query = text(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id SERIAL PRIMARY KEY,
                board_id INT REFERENCES Boards(id),
                table_name VARCHAR(255),
                table_description TEXT,
                table_column_type_detail TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        self.create_table(create_table_query)

    def create_data_management_table(self, data_management_table: DataManagementTable) -> Any:
        query = text(f"""
            INSERT INTO {self.table_name} (board_id, table_name, table_description, table_column_type_detail, created_at, updated_at)
            VALUES (:board_id, :table_name, :table_description, :table_column_type_detail, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, board_id, table_name, table_description, table_column_type_detail, created_at, updated_at;
        """)
        values = {
            "board_id": data_management_table.board_id,
            "table_name": data_management_table.table_name,
            "table_description": data_management_table.table_description,
            "table_column_type_detail": data_management_table.table_column_type_detail,
        }
        table_data_tuple = self.execute_query(query, values)
        table_instance = DataManagementTable(**dict(zip(DataManagementTable.__annotations__, table_data_tuple)))
        return table_instance

    def get_data_management_tables(self) -> Any:
        query = text(f"""
            SELECT * FROM {self.table_name};
        """)
        table_data_list = self.execute_query_all(query)
        table_dict = [DataManagementTable(**dict(zip(DataManagementTable.__annotations__, table_data))) for table_data in table_data_list]
        return table_dict

    def get_data_management_table(self, table_id: int) -> Any:
        query = text(f"""
            SELECT * FROM {self.table_name} WHERE id = :table_id;
        """)
        values = {"table_id": table_id}
        table_data_tuple = self.execute_query(query, values)
        table_instance = DataManagementTable(**dict(zip(DataManagementTable.__annotations__, table_data_tuple)))
        return table_instance

    def update_data_management_table(self, table_id: int, data_management_table: DataManagementTable) -> Any:
        query = text(f"""
            UPDATE {self.table_name}
            SET table_name = :table_name, table_description = :table_description,
                table_column_type_detail = :table_column_type_detail, updated_at = CURRENT_TIMESTAMP
            WHERE id = :table_id
            RETURNING id, board_id, table_name, table_description, table_column_type_detail, created_at, updated_at;
        """)
        values = {
            "table_name": data_management_table.table_name,
            "table_description": data_management_table.table_description,
            "table_column_type_detail": data_management_table.table_column_type_detail,
            "table_id": table_id
        }
        table_data_tuple = self.execute_query(query, values)
        table_instance = DataManagementTable(**dict(zip(DataManagementTable.__annotations__, table_data_tuple)))
        return table_instance

    def delete_data_management_table(self, table_id: int) -> Any:
        query = text(f"""
            DELETE FROM {self.table_name} WHERE id = :table_id
            RETURNING id, board_id, table_name, table_description, table_column_type_detail, created_at, updated_at;
        """)
        values = {"table_id": table_id}
        table_data_tuple = self.execute_query(query, values)
        table_instance = DataManagementTable(**dict(zip(DataManagementTable.__annotations__, table_data_tuple)))
        return table_instance


class TableStatusRepository(BaseRepository):
    def __init__(self):
        super().__init__('TableStatus')  # Corrected table name
        create_table_query = text(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id SERIAL PRIMARY KEY,
                data_management_table_id INT REFERENCES DataManagementTable(id),
                month_year VARCHAR,
                approved BOOLEAN,
                filename VARCHAR,
                file_download_link TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        self.create_table(create_table_query)
        #self.pubsub_publisher = pubsub_v1.PublisherClient()
        #self.pubsub_topic_path = self.pubsub_publisher.topic_path('reliable-vector-429905-e8', 'your-topic-id')


    def upload_file_table_status_for_rag(self, file_content: bytes, table_status: 'TableStatus') -> 'TableStatus':
        # Upload file to Google Cloud Storage
        bucket_name = GCP__BUCKET
        current_month_date = datetime.now().strftime("%Y-%m")
        destination_blob_name = f'{current_month_date}/{table_status.filename}'
        
        # Initialize a storage client
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # Upload the file
        blob.upload_from_string(file_content)

        # Set the file download link
        table_status.file_download_link = f'gs://{bucket_name}/{destination_blob_name}'

        # Insert into the database
        query = text("""
            INSERT INTO TableStatus (data_management_table_id, month_year, approved,
                                     filename, file_download_link, created_at, updated_at)
            VALUES (:data_management_table_id, :month_year, :approved,
                    :filename, :file_download_link, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING *;
        """)

        values = {
            "data_management_table_id": table_status.data_management_table_id,
            "month_year": table_status.month_year,
            "approved": table_status.approved,
            "filename": table_status.filename,
            "file_download_link": table_status.file_download_link
        }

        table_status_data_tuple = self.execute_query(query, values)
        table_status_instance = TableStatus(**dict(zip(TableStatus.__annotations__, table_status_data_tuple)))
        return table_status_instance

    def upload_file_table_status(self, upload_df, table_status: TableStatus) -> TableStatus:

        # Upload DataFrame to Google Bucket
        bucket_name = GCP__BUCKET
        current_month_date = datetime.now().strftime("%Y-%m")
        table_status.file_download_link = f'gs://{bucket_name}/{current_month_date}/{table_status.filename}'
        upload_df.to_csv(table_status.file_download_link, index=False, header=True)
        
        query = text("""
            INSERT INTO TableStatus (data_management_table_id, month_year, approved,
                                    filename, file_download_link, created_at, updated_at)
            VALUES (:data_management_table_id, :month_year, :approved,
                    :filename, :file_download_link, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING *;
        """)

        values = {
            "data_management_table_id": table_status.data_management_table_id,
            "month_year": table_status.month_year,
            "approved": table_status.approved,
            "filename": table_status.filename,
            "file_download_link": table_status.file_download_link
        }

        table_status_data_tuple = self.execute_query(query, values)
        table_status_instance = TableStatus(**dict(zip(TableStatus.__annotations__, table_status_data_tuple)))
        return table_status_instance

    def is_month_data_approved(self, table_id: int, month_year: str) -> bool:
        # Check if the data for the specified month and table is already approved
        query = text(f"""
            SELECT id, approved FROM {self.table_name}
            WHERE data_management_table_id = :table_id AND month_year = :month_year;
        """)  

        values = {"table_id": table_id, "month_year": month_year}
        result = self.execute_query(query, values)
        if result is None:
            return False
        
        elif bool(result[1]) == False:
            #Delete old entry for the same table_id and month_year
            _ = self.delete_table_status(result[0])
        return bool(result[1])
    
    def get_all_table_status(self) -> List[TableStatus]:
        query = text(f"""
            SELECT * FROM {self.table_name};
        """)
        table_status_data_list = self.execute_query_all(query)
        table_status_list = [TableStatus(**dict(zip(TableStatus.__annotations__, status_data))) for status_data in table_status_data_list]
        return table_status_list

    def get_table_status_by_id(self, status_id: int) -> Optional[TableStatus]:
        query = text(f"""
            SELECT * FROM {self.table_name} WHERE id = :status_id;
        """)
        values = {"status_id": status_id}
        status_data_tuple = self.execute_query(query, values)
        
        if status_data_tuple:
            table_status_instance = TableStatus(**dict(zip(TableStatus.__annotations__, status_data_tuple)))
            return table_status_instance
        return None
    
    def update_approval_status(self, status_id: int, new_approval_status: bool) -> TableStatus:
        query = text(f"""
            UPDATE {self.table_name}
            SET approved = :new_approval_status, updated_at = CURRENT_TIMESTAMP
            WHERE id = :status_id
            RETURNING *;
        """)
        values = {"status_id": status_id, "new_approval_status": new_approval_status}
        updated_status_data_tuple = self.execute_query(query, values)

        if updated_status_data_tuple:
            updated_status_instance = TableStatus(**dict(zip(TableStatus.__annotations__, updated_status_data_tuple)))
            return updated_status_instance


    def download_files_by_month_year(self, data_management_table_id: int, month_years: List[str]) -> io.BytesIO:
        """
        Download files associated with a data management table for the specified list of month_years.

        Args:
            db (Session): Database session.
            data_management_table_id (int): ID of the data management table.
            month_years (List[str]): List of month_years for which files should be downloaded.

        Returns:
            io.BytesIO: BytesIO object containing the file content.
        """
        file_content = io.BytesIO()

        for month_year in month_years:
            # Fetch the file record for the specified month_year
            file_record = self.get_file_record(data_management_table_id, month_year)
            if not file_record:
                raise HTTPException(status_code=404, detail=f"No file found for data management table {data_management_table_id} and month {month_year}.")

            # Download the file from Google Bucket
            bucket_name = GCP__BUCKET
            blob_name = file_record.filename

            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.download_to_file(file_content)

        return file_content

# @router.get("/download_files/{data_management_table_id}")
# async def download_files(data_management_table_id: int, month_years: List[str]):
#     repository = YourRepository(db)
#     file_content = repository.download_files_by_month_year(data_management_table_id, month_years)

#     return StreamingResponse(io.BytesIO(file_content.getvalue()), media_type="application/octet-stream")

    def get_file_record(self, data_management_table_id: int, month_year: str) -> Optional[TableStatus]:
        """
        Get the file record for the specified data management table and month_year.

        Args:
            data_management_table_id (int): ID of the data management table.
            month_year (str): Month and year in the format "MMYYYY".

        Returns:
            Optional[TableStatus]: TableStatus instance representing the file record, or None if not found.
        """
        query = text(f"""
            SELECT * FROM {self.table_name}
            WHERE data_management_table_id = :data_management_table_id AND month_year = :month_year;
        """)
        values = {"data_management_table_id": data_management_table_id, "month_year": month_year}
        file_data_tuple = self.execute_query(query, values)

        if file_data_tuple:
            file_instance = TableStatus(**dict(zip(TableStatus.__annotations__, file_data_tuple)))
            return file_instance
        return None
    
    def delete_table_status(self, status_id: int) -> Optional[TableStatus]:
        """
        Delete a TableStatus record by its ID.

        Args:
            status_id (int): ID of the TableStatus record.

        Returns:
            Optional[TableStatus]: Deleted TableStatus instance, or None if not found.
        """
        # Retrieve the TableStatus record before deletion for returning it
        existing_status = self.get_table_status_by_id(status_id)

        # If the record exists, perform the deletion
        if existing_status:
            query = text(f"""
                DELETE FROM {self.table_name} WHERE id = :status_id
                RETURNING *;
            """)
            values = {"status_id": status_id}
            deleted_status_data_tuple = self.execute_query(query, values)

            # Construct TableStatus instance from the returned data
            deleted_status_instance = TableStatus(**dict(zip(TableStatus.__annotations__, deleted_status_data_tuple)))
            return deleted_status_instance

        # If the record does not exist, return None
        return None
    
    def get_table_statuses_for_data_table(self, data_table_id: int) -> List[TableStatus]:
        try:
            query = text(f"""
                SELECT * FROM {self.table_name}
                WHERE data_management_table_id = :data_table_id
            """)
            values = {"data_table_id": data_table_id}
            table_status_data_list = self.execute_query_all(query, values)

            table_status_list = [
                TableStatus(**dict(zip(TableStatus.__annotations__, status_data)))
                for status_data in table_status_data_list
            ]

            return table_status_list
        except Exception as e:
            # Log the exception or handle it as needed
            raise e
    
    
    def get_board_id_for_table_status_id(self, data_management_table_id:int):
        try:
            query = text(f"""
                SELECT dm.board_id
                FROM DataManagementTable dm
                WHERE dm.id = :data_management_table_id;
            """)
            values = {"data_management_table_id": data_management_table_id}
            board_id = self.execute_query(query, values)
            return board_id[0]
        except Exception as ex:
            raise ex