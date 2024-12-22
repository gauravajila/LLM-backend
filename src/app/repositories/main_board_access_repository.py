# repositories/main_board_access_repository.py
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import text
from datetime import datetime
from app.repositories.base_repository import BaseRepository
from app.models.main_board_access import MainBoardAccess
from app.models.permissions import MainBoardPermission

class MainBoardAccessRepository(BaseRepository):
    def __init__(self):
        super().__init__('MainBoardAccess')
        create_table_query = text("""
            CREATE TABLE IF NOT EXISTS MainBoardAccess (
                id SERIAL PRIMARY KEY,
                main_board_id INT REFERENCES MainBoard(id) ON DELETE CASCADE,
                client_user_id INT REFERENCES ClientUsers(id) ON DELETE CASCADE,
                permission VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(main_board_id, client_user_id, permission)
            );
        """)
        self.create_table(create_table_query)

    def grant_permission(self, main_board_id: int, client_user_id: int, permission: MainBoardPermission) -> MainBoardAccess:
        query = text("""
            INSERT INTO MainBoardAccess (main_board_id, client_user_id, permission)
            VALUES (:main_board_id, :client_user_id, :permission)
            ON CONFLICT (main_board_id, client_user_id, permission) 
            DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            RETURNING id, main_board_id, client_user_id, permission, created_at, updated_at;
        """)
        values = {
            "main_board_id": main_board_id,
            "client_user_id": client_user_id,
            "permission": permission.value
        }
        result = self.execute_query(query, values)
        return MainBoardAccess(**dict(zip(MainBoardAccess.__annotations__, result)))

    def revoke_permission(self, main_board_id: int, client_user_id: int, permission: MainBoardPermission) -> Optional[MainBoardAccess]:
        query = text("""
            DELETE FROM MainBoardAccess 
            WHERE main_board_id = :main_board_id 
            AND client_user_id = :client_user_id 
            AND permission = :permission
            RETURNING id, main_board_id, client_user_id, permission, created_at, updated_at;
        """)
        values = {
            "main_board_id": main_board_id,
            "client_user_id": client_user_id,
            "permission": permission.value
        }
        result = self.execute_query(query, values)
        return MainBoardAccess(**dict(zip(MainBoardAccess.__annotations__, result))) if result else None

    def check_permission(self, main_board_id: int, client_user_id: int, permission: MainBoardPermission) -> bool:
        # First check if user is the owner
        owner_query = text("""
            SELECT 1 FROM MainBoard 
            WHERE id = :main_board_id AND client_user_id = :client_user_id;
        """)
        
        owner_result = self.execute_query(owner_query, {
            "main_board_id": main_board_id,
            "client_user_id": client_user_id
        })
        
        if owner_result:
            return True
            
        # Check specific permission
        query = text("""
            SELECT 1 FROM MainBoardAccess 
            WHERE main_board_id = :main_board_id 
            AND client_user_id = :client_user_id 
            AND permission = :permission;
        """)
        values = {
            "main_board_id": main_board_id,
            "client_user_id": client_user_id,
            "permission": permission.value
        }
        result = self.execute_query(query, values)
        return bool(result)

    def get_board_permissions(self, main_board_id: int) -> List[MainBoardAccess]:
        query = text("""
            SELECT id, main_board_id, client_user_id, permission, created_at, updated_at
            FROM MainBoardAccess 
            WHERE main_board_id = :main_board_id;
        """)
        results = self.execute_query_all(query, {"main_board_id": main_board_id})
        return [MainBoardAccess(**dict(zip(MainBoardAccess.__annotations__, result))) for result in results]

    def get_user_permissions(self, client_user_id: int) -> List[MainBoardAccess]:
        query = text("""
            SELECT id, main_board_id, client_user_id, permission, created_at, updated_at
            FROM MainBoardAccess 
            WHERE client_user_id = :client_user_id;
        """)
        results = self.execute_query_all(query, {"client_user_id": client_user_id})
        return [MainBoardAccess(**dict(zip(MainBoardAccess.__annotations__, result))) for result in results]
    
    
    def get_user_board_permissions(
        self, 
        main_board_id: int, 
        client_user_id: int
    ) -> Dict[str, Any]:
        """
        Get all permissions a user has for a specific board along with user details.
        Returns a dictionary containing user information and their permissions.
        
        Args:
            main_board_id (int): The ID of the main board
            client_user_id (int): The ID of the user
            
        Returns:
            Dict containing:
            - user_id: int
            - user_name: str
            - user_email: str
            - permissions: List[MainBoardPermission]
            - is_owner: bool
        """
        # First, check if user is the owner
        owner_query = text("""
            SELECT 
                cu.id as user_id,
                cu.name as user_name,
                cu.email as user_email,
                TRUE as is_owner
            FROM MainBoard mb
            JOIN ClientUsers cu ON mb.client_user_id = cu.id
            WHERE mb.id = :main_board_id 
            AND mb.client_user_id = :client_user_id;
        """)
        
        owner_result = self.execute_query(owner_query, {
            "main_board_id": main_board_id,
            "client_user_id": client_user_id
        })
        
        if owner_result:
            # If user is owner, they have all permissions
            return {
                "user_id": owner_result[0],
                "user_name": owner_result[1],
                "user_email": owner_result[2],
                "is_owner": True,
                "permissions": [perm for perm in MainBoardPermission]
            }
            
        # If not owner, get specific permissions
        permissions_query = text("""
            SELECT 
                cu.id as user_id,
                cu.name as user_name,
                cu.email as user_email,
                ARRAY_AGG(DISTINCT mba.permission) as permissions,
                FALSE as is_owner
            FROM MainBoardAccess mba
            JOIN ClientUsers cu ON mba.client_user_id = cu.id
            WHERE mba.main_board_id = :main_board_id 
            AND mba.client_user_id = :client_user_id
            GROUP BY cu.id, cu.name, cu.email;
        """)
        
        values = {
            "main_board_id": main_board_id,
            "client_user_id": client_user_id
        }
        
        result = self.execute_query(permissions_query, values)
        
        if not result:
            # User has no permissions
            return {
                "user_id": client_user_id,
                "user_name": None,
                "user_email": None,
                "is_owner": False,
                "permissions": []
            }
            
        # Convert string permissions to MainBoardPermission enum
        permissions = [
            MainBoardPermission(perm) 
            for perm in result[3] 
            if perm in [p.value for p in MainBoardPermission]
        ]
        
        return {
            "user_id": result[0],
            "user_name": result[1],
            "user_email": result[2],
            "is_owner": False,
            "permissions": permissions
        }

    def get_users_with_board_permissions(self, main_board_id: int) -> List[Dict[str, Any]]:
        """
        Get all users who have any permissions for a specific board.
        
        Args:
            main_board_id (int): The ID of the main board
            
        Returns:
            List of dictionaries containing user information and their permissions
        """
        query = text("""
            WITH owner AS (
                SELECT 
                    cu.id as user_id,
                    cu.name as user_name,
                    cu.email as user_email,
                    ARRAY['view', 'edit', 'delete', 'create'] as permissions,
                    TRUE as is_owner
                FROM MainBoard mb
                JOIN ClientUsers cu ON mb.client_user_id = cu.id
                WHERE mb.id = :main_board_id
            ),
            other_users AS (
                SELECT 
                    cu.id as user_id,
                    cu.name as user_name,
                    cu.email as user_email,
                    ARRAY_AGG(DISTINCT mba.permission) as permissions,
                    FALSE as is_owner
                FROM MainBoardAccess mba
                JOIN ClientUsers cu ON mba.client_user_id = cu.id
                WHERE mba.main_board_id = :main_board_id
                GROUP BY cu.id, cu.name, cu.email
            )
            SELECT * FROM owner
            UNION ALL
            SELECT * FROM other_users
            ORDER BY is_owner DESC, user_name;
        """)
        
        results = self.execute_query_all(query, {"main_board_id": main_board_id})
        
        users_permissions = []
        for result in results:
            permissions = [
                MainBoardPermission(perm) 
                for perm in result[3] 
                if perm in [p.value for p in MainBoardPermission]
            ]
            
            users_permissions.append({
                "user_id": result[0],
                "user_name": result[1],
                "user_email": result[2],
                "permissions": permissions,
                "is_owner": result[4]
            })
            
        return users_permissions

    def check_user_has_any_permission(self, main_board_id: int, client_user_id: int) -> bool:
        """
        Check if a user has any permissions for a specific board.
        
        Args:
            main_board_id (int): The ID of the main board
            client_user_id (int): The ID of the user
            
        Returns:
            bool: True if user has any permissions, False otherwise
        """
        query = text("""
            SELECT 1
            FROM (
                SELECT 1
                FROM MainBoard
                WHERE id = :main_board_id AND client_user_id = :client_user_id
                UNION
                SELECT 1
                FROM MainBoardAccess
                WHERE main_board_id = :main_board_id 
                AND client_user_id = :client_user_id
                LIMIT 1
            ) AS has_access;
        """)
        
        result = self.execute_query(query, {
            "main_board_id": main_board_id,
            "client_user_id": client_user_id
        })
        
        return bool(result)