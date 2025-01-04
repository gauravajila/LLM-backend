# app/repositories/boards_repository.py

from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select
from app.models.boards import Boards
import os
from dotenv import load_dotenv
from sqlmodel import Session, select, create_engine, or_

# Load environment variables from .env file
load_dotenv()

class BoardsRepository:
    def __init__(self):
        # Get the values from the environment
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
        Boards.metadata.create_all(self.engine)
        
    def create_board(self, board: Boards) -> Boards:
        with Session(self.engine) as session:
            db_board = Boards(
                main_board_id=board.main_board_id,
                name=board.name,
                is_active=board.is_active if board.is_active is not None else True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(db_board)
            session.commit()
            session.refresh(db_board)
            return db_board

    def get_boards(self) -> List[Boards]:
        with Session(self.engine) as session:
            statement = select(Boards)
            boards = session.exec(statement).all()
            return boards

    def get_board(self, board_id: int) -> Optional[Boards]:
        with Session(self.engine) as session:
            statement = select(Boards).where(Boards.id == board_id)
            board = session.exec(statement).first()
            return board

    def update_board(self, board_id: int, board: Boards) -> Optional[Boards]:
        with Session(self.engine) as session:
            db_board = session.get(Boards, board_id)
            if not db_board:
                return None
            
            board_data = board.dict(exclude_unset=True)
            for key, value in board_data.items():
                setattr(db_board, key, value)
            
            db_board.updated_at = datetime.utcnow()
            session.add(db_board)
            session.commit()
            session.refresh(db_board)
            return db_board

    def delete_board(self, board_id: int) -> Optional[Boards]:
        with Session(self.engine) as session:
            db_board = session.get(Boards, board_id)
            if not db_board:
                return None
            
            db_board.is_active = False
            db_board.updated_at = datetime.utcnow()
            session.add(db_board)
            session.commit()
            session.refresh(db_board)
            return db_board

    def get_boards_for_main_boards(self, main_board_id: int) -> List[Boards]:
        with Session(self.engine) as session:
            statement = select(Boards).where(Boards.main_board_id == main_board_id)
            boards = session.exec(statement).all()
            return boards

    def update_board_timestamp(self, board_id: int) -> None:
        with Session(self.engine) as session:
            db_board = session.get(Boards, board_id)
            if db_board:
                db_board.updated_at = datetime.utcnow()
                session.add(db_board)
                session.commit()