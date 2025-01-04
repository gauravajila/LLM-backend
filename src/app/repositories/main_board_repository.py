# repositories/main_board_repository.py
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, or_, and_
from datetime import datetime
from app.models.main_board import MainBoard
from app.models.main_board_access import MainBoardAccess
from app.models.permissions import MainBoardPermission
from fastapi import Depends
import os
from dotenv import load_dotenv
from sqlmodel import Session, select, create_engine, or_

# Load environment variables from .env file
load_dotenv()

class MainBoardRepository:
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
        MainBoard.metadata.create_all(self.engine)
        MainBoardAccess.metadata.create_all(self.engine)
        
        from app.repositories.main_board_access_repository import MainBoardAccessRepository
        self.access_repository = MainBoardAccessRepository()
        self.session = Session(self.engine)

    def create_main_board(self, main_board: MainBoard, client_user_id: int) -> MainBoard:
        main_board.client_user_id = client_user_id
        with Session(self.engine) as session:
            session.add(main_board)
            session.commit()
            session.refresh(main_board)
            
            # Grant all permissions to creator
            for permission in MainBoardPermission:
                self.access_repository.grant_permission(
                    main_board.id,
                    client_user_id,
                    permission
                )
        
        return main_board

    def get_main_board(self, main_board_id: int, client_user_id: int) -> Optional[MainBoard]:
        if not self.access_repository.check_permission(main_board_id, client_user_id, MainBoardPermission.VIEW):
            return None
        
        statement = select(MainBoard).where(MainBoard.id == main_board_id)
        result = self.session.exec(statement).first()
        return result

    def update_main_board(self, main_board_id: int, main_board: MainBoard, client_user_id: int) -> Optional[MainBoard]:
        if not self.access_repository.check_permission(main_board_id, client_user_id, MainBoardPermission.EDIT):
            return None
        
        db_main_board = self.get_main_board(main_board_id, client_user_id)
        if not db_main_board:
            return None
            
        db_main_board.name = main_board.name
        db_main_board.main_board_type = main_board.main_board_type
        db_main_board.updated_at = datetime.utcnow()
        
        self.session.add(db_main_board)
        self.session.commit()
        self.session.refresh(db_main_board)
        return db_main_board

    def delete_main_board(self, main_board_id: int, client_user_id: int) -> Optional[MainBoard]:
        if not self.access_repository.check_permission(main_board_id, client_user_id, MainBoardPermission.DELETE):
            return None
            
        main_board = self.get_main_board(main_board_id, client_user_id)
        if not main_board:
            return None
            
        self.session.delete(main_board)
        self.session.commit()
        return main_board

    def get_all_main_boards(self, client_user_id: int) -> List[MainBoard]:
        statement = select(MainBoard).where(
            or_(
                MainBoard.client_user_id == client_user_id,
                MainBoard.id.in_(
                    select(MainBoardAccess.main_board_id).where(
                        and_(
                            MainBoardAccess.client_user_id == client_user_id,
                            MainBoardAccess.permission == MainBoardPermission.VIEW.value
                        )
                    )
                )
            )
        )
        results = self.session.exec(statement).all()
        return list(results)

    def get_board_users(self, main_board_id: int, client_user_id: int) -> Optional[List[Dict[str, Any]]]:
        if not self.access_repository.check_permission(main_board_id, client_user_id, MainBoardPermission.VIEW):
            return None
            
        statement = select(ClientUsers, MainBoardAccess).join(
            MainBoardAccess, 
            ClientUsers.id == MainBoardAccess.client_user_id
        ).where(MainBoardAccess.main_board_id == main_board_id)
        
        results = self.session.exec(statement).all()
        
        # Group permissions by user
        users_dict = {}
        for user, access in results:
            if user.id not in users_dict:
                users_dict[user.id] = {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "permissions": []
                }
            users_dict[user.id]["permissions"].append(access.permission)
            
        return list(users_dict.values())

    def convert_to_tree_structure(self, data: List[Any], client_user_id: int) -> List[Dict[str, Any]]:
        tree = {}

        for main_board, board in data:
            if not self.access_repository.check_permission(main_board.id, client_user_id, MainBoardPermission.VIEW):
                continue

            if main_board.id not in tree:
                tree[main_board.id] = {
                    "main_board_id": main_board.id,
                    "client_user_id": main_board.client_user_id,
                    "name": main_board.name,
                    "main_board_type": main_board.main_board_type,
                    "is_selected": False,
                    "boards": {},
                    "permissions": self._get_user_permissions_for_board(main_board.id, client_user_id)
                }

            if board and board.id not in tree[main_board.id]["boards"]:
                tree[main_board.id]["boards"][board.id] = {
                    "name": board.name,
                    "is_active": board.is_active,
                    "is_selected": False
                }

        return list(tree.values())

    def _get_user_permissions_for_board(self, main_board_id: int, client_user_id: int) -> List[str]:
        statement = select(MainBoardAccess.permission).where(
            and_(
                MainBoardAccess.main_board_id == main_board_id,
                MainBoardAccess.client_user_id == client_user_id
            )
        )
        results = self.session.exec(statement).all()
        
        # Add all permissions if user is owner
        owner_check = select(MainBoard).where(
            and_(
                MainBoard.id == main_board_id,
                MainBoard.client_user_id == client_user_id
            )
        )
        if self.session.exec(owner_check).first():
            return [perm.value for perm in MainBoardPermission]
            
        return list(results)

    def get_all_info_tree(self, client_user_id: int) -> List[Dict[str, Any]]:
        statement = select(MainBoard, Board).outerjoin(
            Board, MainBoard.id == Board.main_board_id
        ).where(
            or_(
                MainBoard.client_user_id == client_user_id,
                MainBoard.id.in_(
                    select(MainBoardAccess.main_board_id).where(
                        and_(
                            MainBoardAccess.client_user_id == client_user_id,
                            MainBoardAccess.permission == MainBoardPermission.VIEW.value
                        )
                    )
                )
            )
        )
        results = self.session.exec(statement).all()
        return self.convert_to_tree_structure(results, client_user_id)

    def get_filtered_info_tree(self, client_user_id: int, filter_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        conditions = []
        
        if filter_params.get("main_board_type"):
            conditions.append(MainBoard.main_board_type == filter_params["main_board_type"])
            
        if filter_params.get("name"):
            conditions.append(MainBoard.name.ilike(f"%{filter_params['name']}%"))
            
        if filter_params.get("is_active") is not None:
            conditions.append(Board.is_active == filter_params["is_active"])
            
        base_condition = or_(
            MainBoard.client_user_id == client_user_id,
            MainBoard.id.in_(
                select(MainBoardAccess.main_board_id).where(
                    and_(
                        MainBoardAccess.client_user_id == client_user_id,
                        MainBoardAccess.permission == MainBoardPermission.VIEW.value
                    )
                )
            )
        )
        
        conditions.append(base_condition)
        
        statement = select(MainBoard, Board).outerjoin(
            Board, MainBoard.id == Board.main_board_id
        ).where(and_(*conditions))
        
        results = self.session.exec(statement).all()
        return self.convert_to_tree_structure(results, client_user_id)