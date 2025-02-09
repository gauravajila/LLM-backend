# app/repositories/prompt_repository.py
from datetime import datetime
import hashlib
import os
import io
import pandas as pd
from typing import Optional, List, Tuple
from sqlmodel import Session, select, delete
from app.database import engine
from app.models.prompt import Prompt, PromptCreate
from app.models.prompt_response import PromptResponse
from app.models.boards import Boards
from app.models.main_board import MainBoard
from fastapi import HTTPException
from app.models.data_management_table import DataManagementTable, TableStatus
from minio import Minio
from minio.error import S3Error
class PromptRepository:
    def __init__(self):
        #Create tables
        Prompt.metadata.create_all(engine)
        PromptResponse.metadata.create_all(engine)
        self.minio_host = os.getenv("MINIO_HOST", "localhost:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY")
        self.minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.bucket_name = os.getenv("MINIO_BUCKET", "customer-document-storage")

        self._init_minio()
        
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
            
    def create_prompt(self, prompt_create: PromptCreate) -> Prompt:
        
        db_prompt = Prompt(
            board_id=prompt_create.board_id,
            prompt_text=prompt_create.prompt_text,
            prompt_out=prompt_create.prompt_out,
            user_name=prompt_create.user_name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with Session(engine) as session:
            session.add(db_prompt)
            session.commit()
            session.refresh(db_prompt)
            return db_prompt

    def get_prompts_for_board(self, board_id: int) -> List[Prompt]:
        with Session(engine) as session:
            statement = select(Prompt).where(Prompt.board_id == board_id)
            results = session.exec(statement).all()
            return list(results)

    def get_prompts_for_board_in_main_board(self, main_board_id: int, board_id: int) -> List[Prompt]:
        with Session(engine) as session:
            # Note: You'll need to adjust this query based on your actual MainBoard and Boards table structure
            statement = select(Prompt)\
                .join(Boards)\
                .join(MainBoard)\
                .where(Prompt.board_id == board_id)\
                .where(MainBoard.id == main_board_id)
            results = session.exec(statement).all()
            return list(results)

    def tuples_to_combined_dataframe(self, file_records: List[Tuple[str, str]]) -> Tuple[bytes, List[pd.DataFrame], List[str]]:
        """Process file records into dataframes and combined content."""
        result_dict = {}
        dataframes_list = []
        table_names = []

        # Group files by table name
        for download_link, table_name in file_records:
            if table_name not in result_dict:
                result_dict[table_name] = []
                table_names.append(table_name)
            result_dict[table_name].append(download_link)

        # Process each file and combine
        combined_contents = ""
        for table_name, download_links in result_dict.items():
            for link in download_links:
                try:
                    # Parse the MinIO URL to get object name
                    if link.startswith('minio://'):
                        # Split the URL and get only the path part after the bucket name
                        parts = link.split('/')
                        # Find the index of the bucket name and take everything after it
                        bucket_index = parts.index(self.bucket_name)
                        object_name = '/'.join(parts[bucket_index + 1:])
                    else:
                        object_name = link

                    print(f"Accessing MinIO object: {object_name}")
                    print(f"Bucket name: {self.bucket_name}")
                    
                    # Get object data from MinIO
                    response = self.minio_client.get_object(self.bucket_name, object_name)
                    file_data = response.read()
                    
                    # Convert bytes to DataFrame using StringIO
                    df = pd.read_csv(io.StringIO(file_data.decode('utf-8')))
                    print(f"Successfully read DataFrame with shape: {df.shape}")
                    
                    # Convert back to CSV string for combined contents
                    contents = df.to_csv(index=False)
                    combined_contents += contents
                    dataframes_list.append(df)
                    
                except Exception as e:
                    print(f"Error processing file {link}: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error processing file {link}: {str(e)}"
                    )

        return combined_contents.encode(), dataframes_list, table_names

    def get_file_from_minio(self, file_path: str) -> bytes:
        """Download file from MinIO and return its contents."""
        try:
            # Parse the MinIO URL to get object name
            if file_path.startswith('minio://'):
                # Split the URL and get only the path part after the bucket name
                parts = file_path.split('/')
                # Find the index of the bucket name and take everything after it
                bucket_index = parts.index(self.bucket_name)
                object_name = '/'.join(parts[bucket_index + 1:])
            else:
                object_name = file_path

            print(f"Retrieving object from MinIO: {object_name}")
            print(f"Bucket name: {self.bucket_name}")
            
            # Get the object from MinIO
            response = self.minio_client.get_object(self.bucket_name, object_name)
            return response.read()
            
        except S3Error as e:
            print(f"MinIO error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error reading file from MinIO: {str(e)}"
            )
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error reading file: {str(e)}"
            )

    def get_file_download_links_by_board_id(self, board_id: int) -> Tuple[bytes, List[pd.DataFrame], List[str]]:
        """Get file download links and process files for a board.
        
        Args:
            board_id: ID of the board
            
        Returns:
            Tuple containing:
            - Combined CSV content as bytes
            - List of dataframes
            - List of table names
        """
        with Session(engine) as session:
            try:
                # Construct proper SQLAlchemy query using the models
                query = (
                    select(TableStatus.file_download_link, DataManagementTable.table_name)
                    .join(
                        DataManagementTable,
                        TableStatus.data_management_table_id == DataManagementTable.id
                    )
                    .where(DataManagementTable.board_id == board_id)
                    # .where(TableStatus.approved == True)  # Only get approved files
                )
                
                results = session.exec(query).all()
                
                if not results:
                    raise HTTPException(
                        status_code=404,
                        detail=f"No approved files found for board {board_id}"
                    )
                
                return self.tuples_to_combined_dataframe(results)
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error retrieving file links: {str(e)}"
                )

    def get_prompt(self, prompt_id: int) -> Optional[Prompt]:
        with Session(engine) as session:
            statement = select(Prompt).where(Prompt.id == prompt_id)
            return session.exec(statement).first()

    def update_prompt(self, prompt_id: int, prompt: PromptCreate) -> Optional[Prompt]:
        with Session(engine) as session:
            db_prompt = session.get(Prompt, prompt_id)
            if not db_prompt:
                return None
            
            prompt_data = prompt.dict(exclude_unset=True)
            for key, value in prompt_data.items():
                setattr(db_prompt, key, value)
            db_prompt.updated_at = datetime.utcnow()
            
            session.add(db_prompt)
            session.commit()
            session.refresh(db_prompt)
            return db_prompt

    def delete_prompt(self, prompt_id: int) -> Optional[Prompt]:
        with Session(engine) as session:
            prompt = session.get(Prompt, prompt_id)
            if not prompt:
                return None
            
            session.delete(prompt)
            session.commit()
            return prompt

class PromptResponseRepository:
    def __init__(self):
        #Create tables
        Prompt.metadata.create_all(engine)
        PromptResponse.metadata.create_all(engine)
        
    def generate_hash_key(self, contents: bytes, input_text: str) -> str:
        hash_object = hashlib.sha256(contents + input_text.encode())
        return hash_object.hexdigest()

    async def check_existing_response(self, hash_key: str) -> Optional[PromptResponse]:
        with Session(engine) as session:
            statement = select(PromptResponse).where(PromptResponse.hash_key == hash_key)
            return session.exec(statement).first()

    async def save_response_to_database(self, hash_key: str, result: dict) -> PromptResponse:
        prompt_response = PromptResponse(
            board_id=result.get("board_id"),
            prompt_text=result.get("prompt_text", ""),
            prompt_out=result,
            hash_key=hash_key,
        )
        
        with Session(engine) as session:
            session.add(prompt_response)
            session.commit()
            session.refresh(prompt_response)
            return prompt_response