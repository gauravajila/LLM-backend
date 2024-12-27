# app/repositories/ai_documentation_repository.py
from typing import Any
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.ai_documentation import AiDocumentation

class AiDocumentationRepository(BaseRepository):
    def __init__(self):
        super().__init__('AiDocumentation')
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS AiDocumentation (
                id SERIAL PRIMARY KEY,
                board_id INT REFERENCES Boards(id),
                configuration_details TEXT,
                name VARCHAR(255),
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        self.create_table(create_table_query)

    def create_ai_documentation(self, ai_documentation: AiDocumentation) -> Any:
        query = text("""
            INSERT INTO AiDocumentation (board_id, configuration_details, name, created_at, updated_at)
            VALUES (:board_id, :configuration_details, :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, board_id, configuration_details, name, created_at, updated_at;
        """)

        values = {
            "board_id": ai_documentation.board_id,
            "configuration_details": ai_documentation.configuration_details,
            "name": ai_documentation.name,
        }

        ai_documentation_data_tuple = self.execute_query(query, values)
        ai_documentation_instance = AiDocumentation(**dict(zip(AiDocumentation.__annotations__, ai_documentation_data_tuple)))
        return ai_documentation_instance

    def get_all_ai_documentation(self) -> Any:
        query = text("""
            SELECT * FROM AiDocumentation;
        """)

        ai_documentation_data_list = self.execute_query_all(query)
        ai_documentation_list = []

        for doc_data in ai_documentation_data_list:
            ai_documentation_instance = AiDocumentation(**dict(zip(AiDocumentation.__annotations__, doc_data)))
            try:
                ai_documentation_instance.configuration_details = eval(ai_documentation_instance.configuration_details)
            except Exception as ex:
                ai_documentation_instance.configuration_details = ai_documentation_instance.configuration_details
            ai_documentation_list.append(ai_documentation_instance)

        return ai_documentation_list

    def get_ai_documentation(self, doc_id: int) -> Any:
        query = text("""
            SELECT * FROM AiDocumentation WHERE id = :doc_id;
        """)

        values = {"doc_id": doc_id}

        ai_documentation_data_tuple = self.execute_query(query, values)
        if ai_documentation_data_tuple is None:
            return None
        ai_documentation_instance = AiDocumentation(**dict(zip(AiDocumentation.__annotations__, ai_documentation_data_tuple)))
        try:
            ai_documentation_instance.configuration_details = eval(ai_documentation_instance.configuration_details)
        except Exception as ex:
            ai_documentation_instance.configuration_details = ai_documentation_instance.configuration_details
        return ai_documentation_instance

    def update_ai_documentation(self, doc_id: int, ai_documentation: AiDocumentation) -> Any:
        query = text("""
            UPDATE AiDocumentation
            SET board_id = :board_id, configuration_details = :configuration_details, name = :name, updated_at = CURRENT_TIMESTAMP
            WHERE id = :doc_id
            RETURNING id, board_id, configuration_details, name, created_at, updated_at;
        """)

        values = {
            "board_id": ai_documentation.board_id,
            "configuration_details": ai_documentation.configuration_details,
            "name": ai_documentation.name,
            "doc_id": doc_id
        }

        ai_documentation_data_tuple = self.execute_query(query, values)
        if ai_documentation_data_tuple is None:
            return ai_documentation_data_tuple
        ai_documentation_instance = AiDocumentation(**dict(zip(AiDocumentation.__annotations__, ai_documentation_data_tuple)))
        return ai_documentation_instance

    def delete_ai_documentation(self, doc_id: int) -> Any:
        query = text("""
            DELETE FROM AiDocumentation WHERE id = :doc_id
            RETURNING id, board_id, configuration_details, name, created_at, updated_at;
        """)

        values = {"doc_id": doc_id}

        ai_documentation_data_tuple = self.execute_query(query, values)
        if ai_documentation_data_tuple is None:
            return ai_documentation_data_tuple
        ai_documentation_instance = AiDocumentation(**dict(zip(AiDocumentation.__annotations__, ai_documentation_data_tuple)))
        return ai_documentation_instance

    def update_ai_documentation_for_board(self, board_id: int, ai_documentation: AiDocumentation) -> Any:
        """
        Update AI documentation for a specific board.

        Args:
            board_id (int): The ID of the board for which AI documentation needs to be updated.
            ai_documentation (AiDocumentation): The AI documentation object containing updated information.

        Returns:
            Any: Updated AI documentation instance if successful, otherwise None.
        """
        # Check if AI documentation exists for the provided board_id
        existing_documentation = self.get_ai_documentation(board_id)
        
        if existing_documentation:
            # If AI documentation exists, update it
            return self._update_existing_ai_documentation(board_id, ai_documentation)
        else: 
            # If AI documentation doesn't exist, create a new one
            return self.create_ai_documentation(ai_documentation)

    def _update_existing_ai_documentation(self, board_id: int, ai_documentation: AiDocumentation) -> Any:
        """
        Update existing AI documentation.

        Args:
            board_id (int): The ID of the AI documentation to update.
            ai_documentation (AiDocumentation): The AI documentation object containing updated information.

        Returns:
            Any: Updated AI documentation instance if successful, otherwise None.
        """
        query = text("""
            UPDATE AiDocumentation
            SET configuration_details = :configuration_details, name = :name, updated_at = CURRENT_TIMESTAMP
            WHERE board_id = :board_id
            RETURNING id, board_id, configuration_details, name, created_at, updated_at;
        """)

        values = {
            "configuration_details": ai_documentation.configuration_details,
            "name": ai_documentation.name,
            "board_id": board_id
        }

        updated_documentation_data_tuple = self.execute_query(query, values)
        if updated_documentation_data_tuple:
            updated_documentation_instance = AiDocumentation(**dict(zip(AiDocumentation.__annotations__, updated_documentation_data_tuple)))
            return updated_documentation_instance
        return None  # If update fails, return None