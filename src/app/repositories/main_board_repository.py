# repositories/main_board_repository.py
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import text
from datetime import datetime
from app.repositories.base_repository import BaseRepository
from app.models.main_board import MainBoard
from app.models.permissions import MainBoardPermission
from app.repositories.main_board_access_repository import MainBoardAccessRepository
from app.exceptions import PermissionError

class MainBoardRepository(BaseRepository):
    def __init__(self):
        super().__init__('MainBoard')
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS MainBoard (
                id SERIAL PRIMARY KEY,
                client_user_id INT REFERENCES ClientUsers(id),
                name VARCHAR UNIQUE,
                main_board_type VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.create_table(create_table_query)
        self.access_repository = MainBoardAccessRepository()


    def create_main_board(self, main_board: MainBoard, client_user_id: int) -> MainBoard:
        query = text("""
            INSERT INTO MainBoard (client_user_id, name, main_board_type)
            VALUES (:client_user_id, :name, :main_board_type)
            RETURNING id, client_user_id, name, main_board_type, created_at, updated_at;
        """)
        values = {
            "client_user_id": client_user_id,
            "name": main_board.name,
            "main_board_type": main_board.main_board_type
        }
        main_board_data = self.execute_query(query, values)
        main_board_instance = MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data)))
        
        # Grant all permissions to creator
        for permission in MainBoardPermission:
            self.access_repository.grant_permission(
                main_board_instance.id,
                client_user_id,
                permission
            )
        
        return main_board_instance

    def get_main_board(self, main_board_id: int, client_user_id: int) -> MainBoard:
        if not self.access_repository.check_permission(main_board_id, client_user_id, MainBoardPermission.VIEW):
            #raise PermissionError("User does not have view permission for this board")
            return None
        
        query = text("""
            SELECT id, client_user_id, name, main_board_type, created_at, updated_at
            FROM MainBoard WHERE id = :main_board_id;
        """)
        main_board_data = self.execute_query(query, {"main_board_id": main_board_id})
        return MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data)))

    def update_main_board(self, main_board_id: int, main_board: MainBoard, client_user_id: int) -> MainBoard:
        if not self.access_repository.check_permission(main_board_id, client_user_id, MainBoardPermission.EDIT):
            #raise PermissionError("User does not have edit permission for this board")
            return None
        
        query = text("""
            UPDATE MainBoard
            SET name = :name,
                main_board_type = :main_board_type,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :main_board_id
            RETURNING id, client_user_id, name, main_board_type, created_at, updated_at;
        """)
        values = {
            "main_board_id": main_board_id,
            "name": main_board.name,
            "main_board_type": main_board.main_board_type
        }
        main_board_data = self.execute_query(query, values)
        return MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data)))

    def delete_main_board(self, main_board_id: int, client_user_id: int) -> MainBoard:
        if not self.access_repository.check_permission(main_board_id, client_user_id, MainBoardPermission.DELETE):
            #raise PermissionError("User does not have delete permission for this board")
            return None
            
        query = text("""
            DELETE FROM MainBoard 
            WHERE id = :main_board_id
            RETURNING id, client_user_id, name, main_board_type, created_at, updated_at;
        """)
        main_board_data = self.execute_query(query, {"main_board_id": main_board_id})
        return MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data)))

    def get_all_main_boards(self, client_user_id: int) -> List[MainBoard]:
        query = text("""
            SELECT DISTINCT mb.id, mb.client_user_id, mb.name, mb.main_board_type, 
                   mb.created_at, mb.updated_at
            FROM MainBoard mb
            LEFT JOIN MainBoardAccess mba ON mb.id = mba.main_board_id
            WHERE mb.client_user_id = :client_user_id 
            OR (mba.client_user_id = :client_user_id AND mba.permission = :permission);
        """)
        values = {
            "client_user_id": client_user_id,
            "permission": MainBoardPermission.VIEW.value
        }
        main_boards_data = self.execute_query_all(query, values)
        return [MainBoard(**dict(zip(MainBoard.__annotations__, main_board_data))) 
                for main_board_data in main_boards_data]

    def get_board_users(self, main_board_id: int, client_user_id: int) -> List[Dict[str, Any]]:
        if not self.access_repository.check_permission(main_board_id, client_user_id, MainBoardPermission.VIEW):
            #raise PermissionError("User does not have view permission for this board")
            return None
        
        query = text("""
            SELECT DISTINCT cu.id, cu.name, cu.email,
                   ARRAY_AGG(mba.permission) as permissions
            FROM ClientUsers cu
            JOIN MainBoardAccess mba ON cu.id = mba.client_user_id
            WHERE mba.main_board_id = :main_board_id
            GROUP BY cu.id, cu.name, cu.email;
        """)
        return self.execute_query_all(query, {"main_board_id": main_board_id})
    

    def convert_to_tree_structure(self, data: List[Tuple[Any, ...]], client_user_id: int) -> List[Dict[str, Any]]:
        tree = {}

        for item in data:
            main_board_id, client_user_id_owner, main_board_name, main_board_type, board_id, board_name, is_active = item

            # Check if user has permission to view this main board
            if not self.access_repository.check_permission(main_board_id, client_user_id, MainBoardPermission.VIEW):
                continue

            if main_board_id not in tree:
                tree[main_board_id] = {
                    "main_board_id": main_board_id,
                    "client_user_id": client_user_id_owner,
                    "name": main_board_name,
                    "main_board_type": main_board_type,
                    "is_selected": False,
                    "boards": {},
                    "permissions": self._get_user_permissions_for_board(main_board_id, client_user_id)
                }

            if board_id is not None and board_id not in tree[main_board_id]["boards"]:
                tree[main_board_id]["boards"][board_id] = {
                    "name": board_name,
                    "is_active": is_active,
                    "is_selected": False
                }

        return list(tree.values())

    def _get_user_permissions_for_board(self, main_board_id: int, client_user_id: int) -> List[str]:
        """Helper method to get all permissions a user has for a specific board"""
        query = text("""
            SELECT DISTINCT permission 
            FROM MainBoardAccess 
            WHERE main_board_id = :main_board_id 
            AND client_user_id = :client_user_id
            UNION
            SELECT unnest(ARRAY['view', 'edit', 'delete', 'create']) as permission
            FROM MainBoard 
            WHERE id = :main_board_id 
            AND client_user_id = :client_user_id;
        """)
        values = {
            "main_board_id": main_board_id,
            "client_user_id": client_user_id
        }
        results = self.execute_query_all(query, values)
        return [result[0] for result in results]

    def get_all_info_tree(self, client_user_id: int) -> Any:
        """
        Get all main boards and their associated boards that the user has permission to view,
        organized in a tree structure.
        """
        query = text("""
            SELECT DISTINCT
                mb.id AS main_board_id,
                mb.client_user_id AS client_user_id,
                mb.name AS main_board_name,
                mb.main_board_type AS main_board_type,
                b.id AS board_id,
                b.name AS board_name,
                b.is_active AS is_active
            FROM
                MainBoard mb
            LEFT JOIN
                Boards b ON mb.id = b.main_board_id
            WHERE
                mb.client_user_id = :client_user_id
            OR EXISTS (
                SELECT 1 
                FROM MainBoardAccess mba 
                WHERE mba.main_board_id = mb.id 
                AND mba.client_user_id = :client_user_id 
                AND mba.permission = :view_permission
            );
        """)
        
        values = {
            "client_user_id": client_user_id,
            "view_permission": MainBoardPermission.VIEW.value
        }
        
        all_info = self.execute_query_all(query, values)
        tree_output = self.convert_to_tree_structure(all_info, client_user_id)
        return tree_output

    def get_filtered_info_tree(self, client_user_id: int, filter_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get filtered main boards and their associated boards that the user has permission to view,
        organized in a tree structure.
        """
        base_query = """
            SELECT DISTINCT
                mb.id AS main_board_id,
                mb.client_user_id AS client_user_id,
                mb.name AS main_board_name,
                mb.main_board_type AS main_board_type,
                b.id AS board_id,
                b.name AS board_name,
                b.is_active AS is_active
            FROM
                MainBoard mb
            LEFT JOIN
                Boards b ON mb.id = b.main_board_id
            WHERE
                (mb.client_user_id = :client_user_id
                OR EXISTS (
                    SELECT 1 
                    FROM MainBoardAccess mba 
                    WHERE mba.main_board_id = mb.id 
                    AND mba.client_user_id = :client_user_id 
                    AND mba.permission = :view_permission
                ))
        """
        
        filter_conditions = []
        values = {
            "client_user_id": client_user_id,
            "view_permission": MainBoardPermission.VIEW.value
        }

        # Add filter conditions
        if filter_params.get("main_board_type"):
            filter_conditions.append("mb.main_board_type = :board_type")
            values["board_type"] = filter_params["main_board_type"]
        
        if filter_params.get("name"):
            filter_conditions.append("mb.name ILIKE :name")
            values["name"] = f"%{filter_params['name']}%"
        
        if filter_params.get("is_active") is not None:
            filter_conditions.append("b.is_active = :is_active")
            values["is_active"] = filter_params["is_active"]

        if filter_conditions:
            base_query += " AND " + " AND ".join(filter_conditions)

        query = text(base_query)
        all_info = self.execute_query_all(query, values)
        tree_output = self.convert_to_tree_structure(all_info, client_user_id)
        return tree_output