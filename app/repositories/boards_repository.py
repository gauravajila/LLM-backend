# app/repositories/boards_repository.py

from typing import Any
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.models.boards import Boards

class BoardsRepository(BaseRepository):
    def __init__(self):
        super().__init__('Boards')
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS Boards (
                id SERIAL PRIMARY KEY,
                main_board_id INT REFERENCES MainBoard(id),
                client_user_id INT REFERENCES ClientUsers(id),
                name VARCHAR(255),
                is_active BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            );
        """)
        self.create_table(create_table_query)
        
    def create_board(self, board: Boards) -> Any:
        query = text("""
            INSERT INTO Boards (main_board_id, name, created_at, updated_at, is_active)
            VALUES (:main_board_id, :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :is_active)
            RETURNING id, main_board_id, name, created_at, updated_at, is_active;
        """)

        values = {
            "main_board_id": board.main_board_id,
            "name": board.name,
            "is_active": board.is_active if hasattr(board, 'is_active') else True,
        }

        board_data_tuple = self.execute_query(query, values)
        board_instance = Boards(**dict(zip(Boards.__annotations__, board_data_tuple)))
        return board_instance

    def get_boards(self) -> Any:
        query = text("""
            SELECT * FROM Boards;
        """)

        board_data_list = self.execute_query_all(query)
        board_dict = [Boards(**dict(zip(Boards.__annotations__, board_data))) for board_data in board_data_list]
        return board_dict

    def get_board(self, board_id: int, client_user_id: int) -> Any:
        query = text("""
            SELECT * FROM Boards WHERE id = :board_id AND client_user_id = :client_user_id;
        """)
        values = {"board_id": board_id, "client_user_id": client_user_id}
        board_data_tuple = self.execute_query(query, values)
        if not board_data_tuple:
            return None
        board_instance = Boards(**dict(zip(Boards.__annotations__, board_data_tuple)))
        return board_instance


    def update_board(self, board_id: int, board: Boards) -> Any:
        query = text("""
            UPDATE Boards
            SET main_board_id = :main_board_id,
                name = :name,
                is_active = :is_active,  -- Add the update for 'is_active'
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :board_id
            RETURNING id, main_board_id, name, created_at, updated_at, is_active;
        """)

        values = {
            "main_board_id": board.main_board_id,
            "name": board.name,
            "is_active": board.is_active,  # Assuming 'is_active' is a field in the Boards class
            "board_id": board_id
        }

        board_data_tuple = self.execute_query(query, values)
        board_instance = Boards(**dict(zip(Boards.__annotations__, board_data_tuple)))
        return board_instance

    def delete_board(self, board_id: int) -> Any:
        query = text("""
            UPDATE Boards
            SET is_active = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :board_id
            RETURNING id, main_board_id, name, created_at, updated_at, is_active;
        """)

        values = {"board_id": board_id}

        board_data_tuple = self.execute_query(query, values)
        board_instance = Boards(**dict(zip(Boards.__annotations__, board_data_tuple)))
        return board_instance
    
    def get_boards_for_main_boards(self, main_board_id: int) -> Any:
        query = text("""
            SELECT Boards.*
            FROM Boards
            JOIN MainBoard ON Boards.main_board_id = MainBoard.id
            WHERE MainBoard.id = :main_board_id;
        """)

        values = {"main_board_id": main_board_id}

        board_data_list = self.execute_query_all(query, values)
        board_dict = [Boards(**dict(zip(Boards.__annotations__, board_data))) for board_data in board_data_list]
        return board_dict

    def update_board_timestamp(self, board_id: int) -> None:
        query = text("""
            UPDATE Boards
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = :board_id;
        """)

        values = {"board_id": board_id}
        self.execute_query(query, values)