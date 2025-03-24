from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, and_, or_, join
from datetime import datetime
from app.models.main_board_access import MainBoardAccess
from app.models.main_board import MainBoard
from app.models.client_user import ClientUser
from app.models.permissions import MainBoardPermission
from fastapi import Depends
import os
from dotenv import load_dotenv
from sqlmodel import Session, select, create_engine, or_

# Load environment variables from .env file
load_dotenv()

class MainBoardAccessRepository:
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
        MainBoardAccess.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        
    def grant_permission(self, main_board_id: int, client_user_id: int, permission: MainBoardPermission) -> MainBoardAccess:
        """
        Grant a specific permission to a user for a main board.
        
        Args:
            main_board_id (int): The ID of the main board
            client_user_id (int): The ID of the user
            permission (MainBoardPermission): The permission to grant
            
        Returns:
            MainBoardAccess: The created or updated access record
        """
        access = MainBoardAccess(
            main_board_id=main_board_id,
            client_user_id=client_user_id,
            permission=permission.value
        )
        
        # Check for existing permission
        statement = select(MainBoardAccess).where(
            and_(
                MainBoardAccess.main_board_id == main_board_id,
                MainBoardAccess.client_user_id == client_user_id,
                MainBoardAccess.permission == permission.value
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

    def revoke_permission(self, main_board_id: int, client_user_id: int, permission: MainBoardPermission) -> Optional[MainBoardAccess]:
        """
        Revoke a specific permission from a user for a main board.
        
        Args:
            main_board_id (int): The ID of the main board
            client_user_id (int): The ID of the user
            permission (MainBoardPermission): The permission to revoke
            
        Returns:
            Optional[MainBoardAccess]: The deleted access record if found, None otherwise
        """
        statement = select(MainBoardAccess).where(
            and_(
                MainBoardAccess.main_board_id == main_board_id,
                MainBoardAccess.client_user_id == client_user_id,
                MainBoardAccess.permission == permission.value
            )
        )
        access = self.session.exec(statement).first()
        
        if access:
            self.session.delete(access)
            self.session.commit()
            
        return access

    def check_permission(self, main_board_id: int, client_user_id: int, permission: MainBoardPermission) -> bool:
        """
        Check if a user has a specific permission for a main board.
        
        Args:
            main_board_id (int): The ID of the main board
            client_user_id (int): The ID of the user
            permission (MainBoardPermission): The permission to check
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        # Check if user is owner
        owner_check = select(MainBoard).where(
            and_(
                MainBoard.id == main_board_id,
                MainBoard.client_user_id == client_user_id
            )
        )
        if self.session.exec(owner_check).first():
            return True
            
        # Check specific permission
        statement = select(MainBoardAccess).where(
            and_(
                MainBoardAccess.main_board_id == main_board_id,
                MainBoardAccess.client_user_id == client_user_id,
                MainBoardAccess.permission == permission.value
            )
        )
        return bool(self.session.exec(statement).first())

    def get_board_permissions(self, main_board_id: int) -> List[MainBoardAccess]:
        """
        Get all permission records for a specific main board.
        
        Args:
            main_board_id (int): The ID of the main board
            
        Returns:
            List[MainBoardAccess]: List of all permission records
        """
        statement = select(MainBoardAccess).where(
            MainBoardAccess.main_board_id == main_board_id
        )
        return list(self.session.exec(statement).all())

    def get_user_permissions(self, client_user_id: int) -> List[MainBoardAccess]:
        """
        Get all permission records for a specific user.
        
        Args:
            client_user_id (int): The ID of the user
            
        Returns:
            List[MainBoardAccess]: List of all permission records
        """
        statement = select(MainBoardAccess).where(
            MainBoardAccess.client_user_id == client_user_id
        )
        return list(self.session.exec(statement).all())
    
    def get_user_board_permissions(self, main_board_id: int, client_user_id: int) -> Dict[str, Any]:
        """
        Get all permissions a user has for a specific board along with user details.
        
        Args:
            main_board_id (int): The ID of the main board
            client_user_id (int): The ID of the user
            
        Returns:
            Dict containing user information and permissions
        """
        # Check if user is owner
        owner_statement = select(MainBoard, ClientUser).join(
            ClientUser, MainBoard.client_user_id == ClientUser.id
        ).where(
            and_(
                MainBoard.id == main_board_id,
                MainBoard.client_user_id == client_user_id
            )
        )
        owner_result = self.session.exec(owner_statement).first()
        
        if owner_result:
            main_board, user = owner_result
            return {
                "user_id": user.id,
                "user_name": user.name,
                "user_email": user.email,
                "is_owner": True,
                "permissions": [perm for perm in MainBoardPermission]
            }
        
        # Get user permissions
        statement = select(ClientUser, MainBoardAccess).join(
            MainBoardAccess, ClientUser.id == MainBoardAccess.client_user_id
        ).where(
            and_(
                MainBoardAccess.main_board_id == main_board_id,
                MainBoardAccess.client_user_id == client_user_id
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
        
        # First result contains user info
        user, _ = results[0]
        permissions = [MainBoardPermission(access.permission) for _, access in results]
        
        return {
            "user_id": user.id,
            "user_name": user.name,
            "user_email": user.email,
            "is_owner": False,
            "permissions": permissions
        }

    def get_users_with_board_permissions(self, main_board_id: int) -> List[Dict[str, Any]]:
        """
        Get all users who have any permissions for a specific board.
        
        Args:
            main_board_id (int): The ID of the main board
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing user information and permissions
        """
        # Get owner information
        owner_statement = select(MainBoard, ClientUser).join(
            ClientUser, MainBoard.client_user_id == ClientUser.id
        ).where(MainBoard.id == main_board_id)
        owner_result = self.session.exec(owner_statement).first()
        
        results = []
        if owner_result:
            main_board, user = owner_result
            results.append({
                "user_id": user.id,
                "user_name": user.name,
                "user_email": user.email,
                "permissions": [perm for perm in MainBoardPermission],
                "is_owner": True
            })
        
        # Get other users' permissions
        statement = select(ClientUser, MainBoardAccess).join(
            MainBoardAccess, ClientUser.id == MainBoardAccess.client_user_id
        ).where(MainBoardAccess.main_board_id == main_board_id)
        
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
            user_permissions[user.id]["permissions"].append(MainBoardPermission(access.permission))
        
        results.extend(list(user_permissions.values()))
        results.sort(key=lambda x: (not x["is_owner"], x["user_name"] or ""))
        
        return results

    def check_user_has_any_permission(self, main_board_id: int, client_user_id: int) -> bool:
        """
        Check if a user has any permissions for a specific board.
        
        Args:
            main_board_id (int): The ID of the main board
            client_user_id (int): The ID of the user
            
        Returns:
            bool: True if user has any permissions, False otherwise
        """
        # Check if user is owner
        owner_check = select(MainBoard).where(
            and_(
                MainBoard.id == main_board_id,
                MainBoard.client_user_id == client_user_id
            )
        )
        if self.session.exec(owner_check).first():
            return True
        
        # Check for any permissions
        statement = select(MainBoardAccess).where(
            and_(
                MainBoardAccess.main_board_id == main_board_id,
                MainBoardAccess.client_user_id == client_user_id
            )
        )
        return bool(self.session.exec(statement).first())