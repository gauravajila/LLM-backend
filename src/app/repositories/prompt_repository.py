# app/repositories/prompt_repository.py
from datetime import datetime
import hashlib
import pandas as pd
from typing import Optional, List
from sqlmodel import Session, select, delete
from app.database import engine
from app.models.prompt import Prompt, PromptCreate
from app.models.prompt_response import PromptResponse
from app.models.boards import Boards
from app.models.main_board import MainBoard
from fastapi import HTTPException

class PromptRepository:
    def __init__(self):
        #Create tables
        Prompt.metadata.create_all(engine)
        PromptResponse.metadata.create_all(engine)
        
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

    def tuples_to_combined_dataframe(self, tuples_list):
        result_dict = {}
        dataframes_list = []

        for tup in tuples_list:
            table_name = tup[1]
            download_link = tup[0]

            if table_name not in result_dict:
                result_dict[table_name] = []

            result_dict[table_name].append(download_link)

        combined_contents = ""
        table_name_list = []
        for table_name, download_links in result_dict.items():
            table_name_list.append(table_name)
            for file_download_link in download_links:
                df = pd.read_csv(file_download_link)
                contents = df.to_csv(index=False)
                combined_contents += contents
                dataframes_list.append(df)

        return combined_contents.encode(), dataframes_list, table_name_list

    def get_file_download_links_by_board_id(self, board_id: int):
        with Session(engine) as session:
            # Note: Adjust this based on your actual table structure
            statement = select("table_status.file_download_link", "data_management_table.table_name")\
                .join("data_management_table")\
                .where("table_status.board_id" == board_id)
            results = session.exec(statement).all()
            return self.tuples_to_combined_dataframe(results)

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