# app/routers/boards_router.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from app.repositories.boards_repository import BoardsRepository
from app.models.boards import Boards
from app.models.permissions import BoardPermission
from app.authentication import verify_token
from pydantic import BaseModel

router = APIRouter(prefix="/boards", tags=["Boards"])

boards_repository = BoardsRepository()

class BoardPermissionRequest(BaseModel):
    permissions: List[BoardPermission]
    user_id: int

class BoardUserResponse(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    permissions: List[BoardPermission]
    is_owner: bool

@router.post("/", response_model=Boards)
async def create_board(
    board: Boards,
    user_id: int,
    token: str = Depends(verify_token)
):
    created_board = boards_repository.create_board(board, creator_user_id=user_id)
    return created_board

@router.get("/", response_model=List[Boards])
async def get_boards(
    user_id: int,
    token: str = Depends(verify_token)
):
    boards = boards_repository.get_boards(user_id=user_id)
    return boards

@router.get("/{board_id}", response_model=Boards)
async def get_board(
    board_id: int,
    user_id: int,
    token: str = Depends(verify_token)
):
    board = boards_repository.get_board(board_id, user_id=user_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found or access denied")
    return board

@router.put("/{board_id}", response_model=Boards)
async def update_board(
    board_id: int,
    board: Boards,
    user_id: int,
    token: str = Depends(verify_token)
):
    try:
        updated_board = boards_repository.update_board(board_id, board, user_id=user_id)
        if not updated_board:
            raise HTTPException(status_code=404, detail="Board not found")
        return updated_board
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{board_id}", response_model=dict)
async def delete_board(
    board_id: int,
    user_id: int,
    token: str = Depends(verify_token)
):
    try:
        deleted_board = boards_repository.delete_board(board_id, user_id=user_id)
        if not deleted_board:
            raise HTTPException(status_code=404, detail="Board not found")
        return {"status_code": 200, "detail": "Board deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{main_board_id}/boards", response_model=List[Boards])
async def get_boards_for_main_boards(
    main_board_id: int,
    user_id: int,
    token: str = Depends(verify_token)
):
    boards = boards_repository.get_boards_for_main_boards(main_board_id, user_id=user_id)
    return boards

@router.get("/{board_id}/users", response_model=List[BoardUserResponse])
async def get_board_users(
    board_id: int,
    user_id: int,
    token: str = Depends(verify_token)
):
    try:
        users = boards_repository.get_board_users(board_id, admin_user_id=user_id)
        return users
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{board_id}/users", response_model=dict)
async def add_user_to_board(
    board_id: int,
    admin_user_id: int,
    permissions: BoardPermissionRequest,
    token: str = Depends(verify_token)
):
    try:
        boards_repository.add_user_to_board(
            board_id, 
            target_user_id=permissions.user_id,
            permissions=permissions.permissions,
            admin_user_id=admin_user_id
        )
        return {"status_code": 200, "detail": "User added to board successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{board_id}/users/{target_user_id}", response_model=dict)
async def remove_user_from_board(
    board_id: int,
    target_user_id: int,
    user_id: int,
    token: str = Depends(verify_token)
):
    try:
        boards_repository.remove_user_from_board(
            board_id, 
            target_user_id=target_user_id, 
            admin_user_id=user_id
        )
        return {"status_code": 200, "detail": "User removed from board successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{board_id}/users/{target_user_id}/permissions", response_model=dict)
async def modify_user_permissions(
    board_id: int,
    target_user_id: int,
    permissions: BoardPermissionRequest,
    token: str = Depends(verify_token)
):
    try:
        boards_repository.modify_user_permissions(
            board_id,
            target_user_id=target_user_id,
            permissions=permissions.permissions,
            admin_user_id=permissions.user_id
        )
        return {"status_code": 200, "detail": "User permissions updated successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))