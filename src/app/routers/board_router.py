# app/routers/boards_router.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.repositories.boards_repository import BoardsRepository
from app.models.boards import Boards
from app.authentication import verify_token

router = APIRouter(prefix="/boards", tags=["Boards"])

boards_repository = BoardsRepository()

@router.post("/", response_model=Boards)
async def create_board(board: Boards, token: str = Depends(verify_token)):
    created_board = boards_repository.create_board(board)
    return created_board

@router.get("/", response_model=List[Boards])
async def get_boards(token: str = Depends(verify_token)):
    boards = boards_repository.get_boards()
    return boards

@router.get("/{board_id}", response_model=Boards)
async def get_board(board_id: int, token: str = Depends(verify_token)):
    board = boards_repository.get_board(board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board

@router.put("/{board_id}", response_model=Boards)
async def update_board(board_id: int, board: Boards, token: str = Depends(verify_token)):
    updated_board = boards_repository.update_board(board_id, board)
    if not updated_board:
        raise HTTPException(status_code=404, detail="Board not found")
    return updated_board

@router.delete("/{board_id}", response_model=dict)
async def delete_board(board_id: int, token: str = Depends(verify_token)):
    deleted_board = boards_repository.delete_board(board_id)
    if not deleted_board:
        raise HTTPException(status_code=404, detail="Board not found")
    response_data = {"status_code": 200, "detail": "Board deleted successfully"}
    return response_data

@router.get("/{main_board_id}/boards", response_model=List[Boards])
async def get_boards_for_main_boards(main_board_id:int, token: str = Depends(verify_token)):
    boards = boards_repository.get_boards_for_main_boards(main_board_id)
    return boards