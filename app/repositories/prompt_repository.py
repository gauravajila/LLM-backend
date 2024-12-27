# app/repositories/prompt_repository.py
from datetime import datetime
import hashlib
import pandas as pd
from typing import Optional, List
from app.database import get_database_connection
from app.models.prompt import Prompt, PromptCreate
from typing import Any
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.prompt_response import PromptResponse

class PromptRepository(BaseRepository):
    def __init__(self):
        super().__init__('Prompts')
        create_table_query = text(f"""
                                CREATE TABLE IF NOT EXISTS {self.table_name} (
                                    id SERIAL PRIMARY KEY,
                                    board_id INT REFERENCES Boards(id),
                                    prompt_text TEXT,
                                    prompt_out TEXT,
                                    created_at TIMESTAMP,
                                    updated_at TIMESTAMP, 
                                    user_name TEXT
                            );
        """)
        self.create_table(create_table_query)

    def create_prompt(self, prompt_create: Prompt):
        query = text(f"""
            INSERT INTO {self.table_name} (board_id, prompt_text, prompt_out, created_at, updated_at, user_name)
            VALUES (:board_id, :prompt_text, :prompt_out, :created_at, :updated_at, :user_name)
            RETURNING id, board_id, prompt_text, prompt_out, created_at, updated_at, user_name;
        """)

        values = {
            "board_id": prompt_create.board_id,
            "prompt_text": prompt_create.prompt_text,
            "prompt_out": prompt_create.prompt_out,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "user_name": prompt_create.user_name
        }

        created_prompt_tuple = self.execute_query(query, values)
        created_prompt = Prompt(**dict(zip(Prompt.__annotations__, created_prompt_tuple)))
        return created_prompt

    def get_prompts_for_board(self, board_id: int) -> List[Prompt]:
        query = text(f"""
            SELECT id, board_id, prompt_text, prompt_out, created_at, updated_at, user_name
            FROM {self.table_name}
            WHERE board_id = :board_id;
        """)

        values = {"board_id": board_id}

        prompts_data_list = self.execute_query_all(query, values)
        prompts_dict = [Prompt(**dict(zip(Prompt.__annotations__, prompts_data))) for prompts_data in prompts_data_list]
        return prompts_dict

    def get_prompts_for_board_in_main_board(self, main_board_id: int, board_id: int) -> List[Prompt]:
        query = text("""
            SELECT Prompts.*
            FROM Prompts
            JOIN Boards ON Prompts.board_id = Boards.id
            JOIN MainBoard ON Boards.main_board_id = MainBoard.id
            WHERE Boards.id = :board_id 
            AND MainBoard.id = :main_board_id;
        """)

        values = {"main_board_id": main_board_id,
                  "board_id": board_id}

        prompts_data_list = self.execute_query_all(query, values)
        prompts_dict = [Prompt(**dict(zip(Prompt.__annotations__, prompts_data))) for prompts_data in prompts_data_list]
        return prompts_dict

    def tuples_to_combined_dataframe(self, tuples_list):
        result_dict = {}
        dataframes_list = []

        for tup in tuples_list:
            table_name = tup[1]
            download_link = tup[0]

            if table_name not in result_dict:
                result_dict[table_name] = []

            result_dict[table_name].append(download_link)

        combined_contents = ""  # Initialize an empty string to store the combined CSV content
        table_name_list = list()
        for table_name, download_links in result_dict.items():
            # To do: Need to combine all dataframe for single Table
            # Every table should have its own dataframe
            table_name_list.append(table_name)
            for file_download_link in download_links:
                df = pd.read_csv(file_download_link)
                contents = df.to_csv(index=False)
                combined_contents += contents  # Concatenate the CSV strings
                dataframes_list.append(df)

        return combined_contents.encode(), dataframes_list, table_name_list

    def get_file_download_links_by_board_id(self, board_id: int):
        query = text(f"""SELECT ts.file_download_link, dt.table_name
            FROM TableStatus ts
            JOIN DataManagementTable dt ON ts.data_management_table_id = dt.id
            WHERE board_id = :board_id;
        """)

        values = {"board_id": board_id}

        download_links_by_board_id_list = self.execute_query_all(query, values)
        return self.tuples_to_combined_dataframe(download_links_by_board_id_list)

    def get_prompt(self, prompt_id: int) -> Optional[Prompt]:
        query = text(f"""
            SELECT id, board_id, prompt_text, prompt_out, created_at, updated_at, user_name
            FROM {self.table_name}
            WHERE id = :prompt_id;
        """)

        values = {"prompt_id": prompt_id}

        prompt_data = self.execute_query(query, values)

        if prompt_data:
            return Prompt(**dict(zip(Prompt.__annotations__, prompt_data)))
        return None

    def update_prompt(self, prompt_id: int, prompt: PromptCreate) -> Optional[Prompt]:
        query = text(f"""
            UPDATE {self.table_name}
            SET prompt_text = :prompt_text, prompt_out = :prompt_out, updated_at = :updated_at, user_name = :user_name
            WHERE id = :prompt_id
            RETURNING id, board_id, prompt_text, prompt_out, created_at, updated_at, user_name;
        """)

        values = {
            "prompt_text": prompt.prompt_text,
            "prompt_out": prompt.prompt_out,
            "updated_at": datetime.utcnow(),
            "user_name": prompt.user_name,
            "prompt_id": prompt_id
        }

        updated_prompt_data = self.execute_query(query, values)

        if updated_prompt_data:
            return Prompt(**dict(zip(Prompt.__annotations__, updated_prompt_data)))
        return None

    def delete_prompt(self, prompt_id: int) -> Optional[Prompt]:
        query = text(f"""
            DELETE FROM {self.table_name}
            WHERE id = :prompt_id
            RETURNING id, board_id, prompt_text, prompt_out, created_at, updated_at, user_name;
        """)

        values = {"prompt_id": prompt_id}

        deleted_prompt_data = self.execute_query(query, values)

        if deleted_prompt_data:
            return Prompt(**dict(zip(Prompt.__annotations__, deleted_prompt_data)))
        return None

class PromptResponseRepository(BaseRepository):
    def __init__(self):
        super().__init__('Prompts_response')
        create_table_query = text(f"""
                                CREATE TABLE IF NOT EXISTS {self.table_name} (
                                    id SERIAL PRIMARY KEY,
                                    board_id INT REFERENCES Boards(id),
                                    prompt_text TEXT,
                                    prompt_out JSON,
                                    created_at TIMESTAMP,
                                    updated_at TIMESTAMP,
                                    hash_key TEXT
                            );
        """)
        self.create_table(create_table_query)

    # Assuming you have a function to generate hash key
    def generate_hash_key(self, contents: bytes, input_text: str) -> str:
        # Implement your logic to generate a unique hash key
        # This could be a hash function like MD5 or SHA-256
        # Here's an example using SHA-256 for illustration purposes
        hash_object = hashlib.sha256(contents + input_text.encode())
        return hash_object.hexdigest()

    async def check_existing_response(self, hash_key: str) -> Optional[PromptResponse]:
        # Implement your logic to check if the response with the given hash key exists in the database
        # You may need to use an asynchronous database library like databases or sqlalchemy-asyncio
        # Return the existing response if found, otherwise return None

        query = text(f"SELECT * FROM {self.table_name} WHERE hash_key = :hash_key")
        values = {"hash_key": hash_key}

        response_data_tuple = self.execute_query(query, values)

        if response_data_tuple:
            return response_data_tuple
        else:
            return None

    async def save_response_to_database(self, hash_key: str, result: dict) -> PromptResponse:
        # Implement your logic to save the response and its hash key to the Prompts_response table
        # You may need to use an asynchronous database library like databases or sqlalchemy-asyncio

        query = text(f"""
            INSERT INTO {self.table_name} (board_id, prompt_text, prompt_out, created_at, updated_at, hash_key)
            VALUES (:board_id, :prompt_text, :prompt_out, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :hash_key)
            RETURNING id, board_id, prompt_text, prompt_out, created_at, updated_at, hash_key;
        """)

        values = {
            "board_id": result.get("board_id"),  # Assuming there's a board_id in the result dictionary
            "prompt_text": result.get("prompt_text", ""),
            "prompt_out": result,
            "hash_key": hash_key,
            "user_name": result.get("user_name", "")
        }

        response_data_tuple = self.execute_query(query, values) 
        #return PromptResponse(**dict(zip(PromptResponse.__annotations__, response_data_tuple)))