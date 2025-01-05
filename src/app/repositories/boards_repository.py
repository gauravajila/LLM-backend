# app/repositories/boards_repository.py

from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select, and_
from app.models.boards import Boards
from app.models.board_access import BoardAccess
from app.models.permissions import BoardPermission
from app.repositories.board_access_repository import BoardAccessRepository
import os
from dotenv import load_dotenv
from sqlmodel import Session, select, create_engine, or_
from fastapi import HTTPException

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
        self.access_repository = BoardAccessRepository()
        
    def create_board(self, board: Boards, creator_user_id: int) -> Boards:
        """
        Create a new board and set up initial permissions for the creator.
        """
        with Session(self.engine) as session:
            # Create the board
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
            
            # Grant all permissions to the creator
            for permission in BoardPermission:
                self.access_repository.grant_permission(
                    board_id=db_board.id,
                    client_user_id=creator_user_id,
                    permission=permission
                )
            
            return db_board

    def get_boards(self, user_id: int) -> List[Boards]:
        """
        Get all boards that the user has access to.
        """
        with Session(self.engine) as session:
            # Get boards where user has direct access
            access_statement = select(BoardAccess.board_id).where(
                BoardAccess.client_user_id == user_id
            )
            accessible_board_ids = session.exec(access_statement).all()
            
            # Get boards where user has access through main board
            statement = select(Boards).where(
                or_(
                    Boards.id.in_(accessible_board_ids),
                    Boards.is_active == True  # Include active boards where user might have main board access
                )
            )
            boards = []
            for board in session.exec(statement).all():
                if self.access_repository.check_user_has_any_permission(board.id, user_id):
                    boards.append(board)
            return boards

    def get_board(self, board_id: int, user_id: int) -> Optional[Boards]:
        """
        Get a specific board if the user has access to it.
        """
        with Session(self.engine) as session:
            statement = select(Boards).where(Boards.id == board_id)
            board = session.exec(statement).first()
            
            if board and self.access_repository.check_user_has_any_permission(board_id, user_id):
                return board
            return None

    def update_board(self, board_id: int, board: Boards, user_id: int) -> Optional[Boards]:
        """
        Update a board if the user has edit permission.
        """
        with Session(self.engine) as session:
            # Check if user has edit permission
            if not self.access_repository.check_permission(board_id, user_id, BoardPermission.EDIT):
                raise HTTPException(status_code=403, detail="User does not have edit permission")
            
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

    def delete_board(self, board_id: int, user_id: int) -> Optional[Boards]:
        """
        Soft delete a board if the user has delete permission.
        """
        with Session(self.engine) as session:
            # Check if user has delete permission
            if not self.access_repository.check_permission(board_id, user_id, BoardPermission.DELETE):
                raise HTTPException(status_code=403, detail="User does not have delete permission")
            
            db_board = session.get(Boards, board_id)
            if not db_board:
                return None
            
            db_board.is_active = False
            db_board.updated_at = datetime.utcnow()
            session.add(db_board)
            session.commit()
            session.refresh(db_board)
            return db_board

    def get_boards_for_main_boards(self, main_board_id: int, user_id: int) -> List[Boards]:
        """
        Get all boards for a main board that the user has access to.
        """
        with Session(self.engine) as session:
            statement = select(Boards).where(Boards.main_board_id == main_board_id)
            boards = []
            for board in session.exec(statement).all():
                if self.access_repository.check_user_has_any_permission(board.id, user_id):
                    boards.append(board)
            return boards

    def update_board_timestamp(self, board_id: int, user_id: int) -> None:
        """
        Update board timestamp if user has edit permission.
        """
        with Session(self.engine) as session:
            # Check if user has edit permission
            if not self.access_repository.check_permission(board_id, user_id, BoardPermission.EDIT):
                raise HTTPException(status_code=403, detail="User does not have edit permission")
            
            db_board = session.get(Boards, board_id)
            if db_board:
                db_board.updated_at = datetime.utcnow()
                session.add(db_board)
                session.commit()

    def add_user_to_board(self, board_id: int, target_user_id: int, 
                         permissions: List[BoardPermission], admin_user_id: int) -> None:
        """
        Add a user to a board with specified permissions.
        """
        # Check if admin user has permission to manage users
        if not self.access_repository.check_permission(board_id, admin_user_id, BoardPermission.MANAGE_USERS):
            raise HTTPException(status_code=403, detail="User does not have permission to manage users")
            
        for permission in permissions:
            self.access_repository.grant_permission(board_id, target_user_id, permission)

    def remove_user_from_board(self, board_id: int, target_user_id: int, admin_user_id: int) -> None:
        """
        Remove a user's access from a board.
        """
        # Check if admin user has permission to manage users
        if not self.access_repository.check_permission(board_id, admin_user_id, BoardPermission.MANAGE_USERS):
            raise HTTPException(status_code=403, detail="User does not have permission to manage users")
            
        # Get all user's permissions and revoke them
        user_permissions = self.access_repository.get_user_board_permissions(board_id, target_user_id)
        for permission in user_permissions["permissions"]:
            self.access_repository.revoke_permission(board_id, target_user_id, permission)

    def modify_user_permissions(self, board_id: int, target_user_id: int, 
                              permissions: List[BoardPermission], admin_user_id: int) -> None:
        """
        Modify a user's permissions for a board.
        """
        # Check if admin user has permission to manage users
        if not self.access_repository.check_permission(board_id, admin_user_id, BoardPermission.MANAGE_USERS):
            raise HTTPException(status_code=403, detail="User does not have permission to manage users")
            
        # Remove all existing permissions
        current_permissions = self.access_repository.get_user_board_permissions(board_id, target_user_id)
        for permission in current_permissions["permissions"]:
            self.access_repository.revoke_permission(board_id, target_user_id, permission)
            
        # Add new permissions
        for permission in permissions:
            self.access_repository.grant_permission(board_id, target_user_id, permission)

    def get_board_users(self, board_id: int, admin_user_id: int) -> List[dict]:
        """
        Get all users who have access to a board and their permissions.
        """
        # Check if admin user has permission to view users
        if not self.access_repository.check_permission(board_id, admin_user_id, BoardPermission.VIEW_USERS):
            raise HTTPException(status_code=403, detail="User does not have permission to view users")
            
        return self.access_repository.get_users_with_board_permissions(board_id)