# repositories/board_access_repository.py
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, and_, or_, join
from datetime import datetime
from app.models.board_access import BoardAccess
from app.models.boards import Boards
from app.models.client_user import ClientUser
from app.models.permissions import BoardPermission
from fastapi import Depends
import os
from dotenv import load_dotenv
from sqlmodel import Session, select, create_engine, or_

# Load environment variables from .env file
load_dotenv()

class BoardAccessRepository:
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
        BoardAccess.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        
    def grant_permission(self, board_id: int, client_user_id: int, permission: BoardPermission) -> BoardAccess:
        """
        Grant a specific permission to a user for a board.
        """
        access = BoardAccess(
            board_id=board_id,
            client_user_id=client_user_id,
            permission=permission.value
        )
        
        statement = select(BoardAccess).where(
            and_(
                BoardAccess.board_id == board_id,
                BoardAccess.client_user_id == client_user_id,
                BoardAccess.permission == permission.value
            )
        )
        existing = self.session.exec(statement).first()
        
        if existing:
            existing.updated_at = datetime.utcnow()
            self.session.add(existing)
            access = existing
        else:
            self.session.add(access)
            
        self.session.commit()
        self.session.refresh(access)
        return access

    def revoke_permission(self, board_id: int, client_user_id: int, permission: BoardPermission) -> Optional[BoardAccess]:
        """
        Revoke a specific permission from a user for a board.
        """
        statement = select(BoardAccess).where(
            and_(
                BoardAccess.board_id == board_id,
                BoardAccess.client_user_id == client_user_id,
                BoardAccess.permission == permission.value
            )
        )
        access = self.session.exec(statement).first()
        
        if access:
            self.session.delete(access)
            self.session.commit()
            
        return access

    def check_permission(self, board_id: int, client_user_id: int, permission: BoardPermission) -> bool:
        """
        Check if a user has a specific permission for a board.
        """
        # First check main board permissions through the board's main_board_id
        board_statement = select(Boards).where(Boards.id == board_id)
        board = self.session.exec(board_statement).first()
        if board:
            from app.repositories.main_board_access_repository import MainBoardAccessRepository
            main_board_repo = MainBoardAccessRepository()
            if main_board_repo.check_permission(board.main_board_id, client_user_id, permission):
                return True
        
        # Then check board-specific permissions
        statement = select(BoardAccess).where(
            and_(
                BoardAccess.board_id == board_id,
                BoardAccess.client_user_id == client_user_id,
                BoardAccess.permission == permission.value
            )
        )
        return bool(self.session.exec(statement).first())

    def get_board_permissions(self, board_id: int) -> List[BoardAccess]:
        """
        Get all permission records for a specific board.
        """
        statement = select(BoardAccess).where(
            BoardAccess.board_id == board_id
        )
        return list(self.session.exec(statement).all())

    def get_user_permissions(self, client_user_id: int) -> List[BoardAccess]:
        """
        Get all permission records for a specific user.
        """
        statement = select(BoardAccess).where(
            BoardAccess.client_user_id == client_user_id
        )
        return list(self.session.exec(statement).all())
    
    def get_user_board_permissions(self, board_id: int, client_user_id: int) -> Dict[str, Any]:
        """
        Get all permissions a user has for a specific board along with user details.
        """
        # First check main board permissions
        board_statement = select(Boards).where(Boards.id == board_id)
        board = self.session.exec(board_statement).first()
        
        if board:
            from app.repositories.main_board_access_repository import MainBoardAccessRepository
            main_board_repo = MainBoardAccessRepository()
            main_board_perms = main_board_repo.get_user_board_permissions(board.main_board_id, client_user_id)
            if main_board_perms["is_owner"]:
                return main_board_perms
        
        # Get board-specific permissions
        statement = select(ClientUser, BoardAccess).join(
            BoardAccess, ClientUser.id == BoardAccess.client_user_id
        ).where(
            and_(
                BoardAccess.board_id == board_id,
                BoardAccess.client_user_id == client_user_id
            )
        )
        results = self.session.exec(statement).all()
        
        if not results:
            return {
                "user_id": client_user_id,
                "user_name": None,
                "user_email": None,
                "is_owner": False,
                "permissions": []
            }
        
        user, _ = results[0]
        permissions = [BoardPermission(access.permission) for _, access in results]
        
        return {
            "user_id": user.id,
            "user_name": user.name,
            "user_email": user.email,
            "is_owner": False,
            "permissions": permissions
        }

    def get_users_with_board_permissions(self, board_id: int) -> List[Dict[str, Any]]:
        """
        Get all users who have any permissions for a specific board.
        """
        # First get main board permissions
        board_statement = select(Boards).where(Boards.id == board_id)
        board = self.session.exec(board_statement).first()
        
        results = []
        if board:
            from app.repositories.main_board_access_repository import MainBoardAccessRepository
            main_board_repo = MainBoardAccessRepository()
            main_board_users = main_board_repo.get_users_with_board_permissions(board.main_board_id)
            results.extend(main_board_users)
        
        # Get board-specific permissions
        statement = select(ClientUser, BoardAccess).join(
            BoardAccess, ClientUser.id == BoardAccess.client_user_id
        ).where(BoardAccess.board_id == board_id)
        
        user_permissions = {}
        for user, access in self.session.exec(statement).all():
            if user.id not in user_permissions:
                user_permissions[user.id] = {
                    "user_id": user.id,
                    "user_name": user.name,
                    "user_email": user.email,
                    "permissions": [],
                    "is_owner": False
                }
            user_permissions[user.id]["permissions"].append(BoardPermission(access.permission))
        
        # Merge with existing results, avoiding duplicates
        for user_data in user_permissions.values():
            existing_user = next((u for u in results if u["user_id"] == user_data["user_id"]), None)
            if existing_user:
                existing_user["permissions"].extend(user_data["permissions"])
            else:
                results.append(user_data)
        
        results.sort(key=lambda x: (not x["is_owner"], x["user_name"] or ""))
        return results

    def check_user_has_any_permission(self, board_id: int, client_user_id: int) -> bool:
        """
        Check if a user has any permissions for a specific board.
        """
        # First check main board permissions
        board_statement = select(Boards).where(Boards.id == board_id)
        board = self.session.exec(board_statement).first()
        
        if board:
            from app.repositories.main_board_access_repository import MainBoardAccessRepository
            main_board_repo = MainBoardAccessRepository()
            if main_board_repo.check_user_has_any_permission(board.main_board_id, client_user_id):
                return True
        
        # Check board-specific permissions
        statement = select(BoardAccess).where(
            and_(
                BoardAccess.board_id == board_id,
                BoardAccess.client_user_id == client_user_id
            )
        )
        return bool(self.session.exec(statement).first())