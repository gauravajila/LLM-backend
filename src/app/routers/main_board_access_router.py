# app/routers/main_board_access_router.py
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum
from app.models.permissions import MainBoardPermission
from app.repositories.main_board_repository import MainBoardRepository
from app.repositories.main_board_access_repository import MainBoardAccessRepository

# Pydantic models for request/response
class PermissionType(str, Enum):
    VIEW = "view"
    EDIT = "edit"
    DELETE = "delete"
    CREATE = "create"

class PermissionRequest(BaseModel):
    client_user_id: int
    permissions: List[PermissionType]

class BatchPermissionRequest(BaseModel):
    permissions_data: List[PermissionRequest]

class UserPermissionResponse(BaseModel):
    client_user_id: int
    permissions: List[PermissionType]
    user_name: Optional[str]
    user_email: Optional[str]

# Router setup
router = APIRouter(prefix="/main-boards/access", tags=["Main Board Access"])

# Repository instances
main_board_repository = MainBoardRepository()
access_repository = MainBoardAccessRepository()

@router.post("/{main_board_id}/grant", response_model=UserPermissionResponse)
async def grant_board_permissions(
    main_board_id: int,
    permission_request: PermissionRequest,
    current_user_id: int
):
    """Grant permissions to a user for a specific board"""
    try:
        # Verify if current user has admin rights
        if not access_repository.check_permission(main_board_id, current_user_id, MainBoardPermission.EDIT):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify board access"
            )

        # Grant each requested permission
        for permission in permission_request.permissions:
            access_repository.grant_permission(
                main_board_id,
                permission_request.client_user_id,
                MainBoardPermission(permission)
            )

        # Get updated permissions for response
        user_permissions = access_repository.get_user_board_permissions(
            main_board_id,
            permission_request.client_user_id
        )
        
        #print(user_permissions)
        
        return UserPermissionResponse(
            client_user_id=permission_request.client_user_id,
            permissions=user_permissions.get("permissions"),
            user_name=user_permissions.get("user_name"),
            user_email=user_permissions.get("user_email")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant permissions: {str(e)}"
        )

@router.post("/{main_board_id}/revoke", response_model=UserPermissionResponse)
async def revoke_board_permissions(
    main_board_id: int,
    permission_request: PermissionRequest,
    current_user_id: int
):
    """Revoke permissions from a user for a specific board"""
    try:
        # Verify if current user has admin rights
        if not access_repository.check_permission(main_board_id, current_user_id, MainBoardPermission.EDIT):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify board access"
            )

        # Revoke each requested permission
        for permission in permission_request.permissions:
            access_repository.revoke_permission(
                main_board_id,
                permission_request.client_user_id,
                MainBoardPermission(permission)
            )

        # Get updated permissions for response
        user_permissions = access_repository.get_user_board_permissions(
            main_board_id,
            permission_request.client_user_id
        )
        
        return UserPermissionResponse(
            client_user_id=permission_request.client_user_id,
            permissions=user_permissions.get("permissions"),
            user_name=user_permissions.get("user_name"),
            user_email=user_permissions.get("user_email")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke permissions: {str(e)}"
        )

@router.get("/{main_board_id}/users", response_model=List[UserPermissionResponse])
async def get_board_users(main_board_id: int, current_user_id: int):
    """Get all users and their permissions for a specific board"""
    try:
        # Verify if current user has view rights
        if not access_repository.check_permission(main_board_id, current_user_id, MainBoardPermission.VIEW):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view board access"
            )

        # Get all users with their permissions
        board_users = main_board_repository.get_board_users(main_board_id, current_user_id)
        
        return [
            UserPermissionResponse(
                client_user_id=user[0],       # Access 'id'
                user_name=user[1],           # Access 'name'
                user_email=user[2],          # Access 'email'
                permissions=user[3]          # Access 'permissions'
            )
            for user in board_users
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get board users: {str(e)}"
        )

@router.post("/{main_board_id}/batch", response_model=List[UserPermissionResponse])
async def batch_update_permissions(
    main_board_id: int,
    batch_request: BatchPermissionRequest,
    current_user_id: int
):
    """Update permissions for multiple users in a single request"""
    try:
        # Verify if current user has admin rights
        if not access_repository.check_permission(main_board_id, current_user_id, MainBoardPermission.EDIT):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify board access"
            )

        responses = []
        for permission_request in batch_request.permissions_data:
            # Grant each permission
            for permission in permission_request.permissions:
                access_repository.grant_permission(
                    main_board_id,
                    permission_request.client_user_id,
                    MainBoardPermission(permission)
                )

            # Get updated permissions
            user_permissions = access_repository.get_user_board_permissions(
                main_board_id,
                permission_request.client_user_id
            )
            
            responses.append(UserPermissionResponse(
                client_user_id=permission_request.client_user_id,
                permissions=user_permissions.get("permissions"),
                user_name=user_permissions.get("user_name"),
                user_email=user_permissions.get("user_email")
            ))

        return responses

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update permissions: {str(e)}"
        )

@router.get("/user/{user_id}/boards", response_model=List[dict])
async def get_user_accessible_boards(user_id: int, current_user_id: int):
    """Get all boards that a user has access to, with their permission levels"""
    try:
        # Only allow users to view their own permissions or admin users
        if current_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own board access"
            )

        # Get all boards with permissions
        accessible_boards = main_board_repository.get_all_info_tree(user_id)
        return accessible_boards

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get accessible boards: {str(e)}"
        )