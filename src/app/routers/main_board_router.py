# app/routers/main_board_router.py
import os
import traceback
from typing import List
from app.models.main_board import MainBoard
from app.repositories.main_board_repository import MainBoardRepository
from app.models.boards import Boards 
from app.models.main_board_access import MainBoardAccess 
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status, Header, Security
from fastapi.security import APIKeyHeader
from app.authentication import verify_token
from app.database import get_db
from sqlalchemy.orm import Session
from typing import Dict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

# Load environment variables from .env file

        
router = APIRouter(prefix="/main-boards", tags=["Main Boards"])

# Creating an instance of the MainBoardRepository
main_board_repository = MainBoardRepository()

@router.post("/", response_model=MainBoard)
async def create_main_board(main_board: MainBoard, client_user_id: int, token: str = Depends(verify_token)):
    try:
        created_main_board = main_board_repository.create_main_board(main_board, client_user_id)
        return created_main_board
    except HTTPException as e:
        raise e

@router.get("/", response_model=List[MainBoard])
async def get_all_main_boards(client_user_id: int, token: str = Depends(verify_token)):
    main_boards = main_board_repository.get_all_main_boards(client_user_id)
    # order = ["ANALYSIS", "FORECASTING", "REVENUE", "PROFITABILITY", "COGS", "CASH FLOW", "BUDGET", "VARIANCE ANALYSIS"]
    # main_boards = sorted(main_boards, key=lambda x: order.index(x.name))
    return main_boards

@router.get("/get_all_info_tree", response_model=list)
async def get_all_info_tree(client_user_id: int, token: str = Depends(verify_token)):
    try:
        all_info_tree = main_board_repository.get_all_info_tree(client_user_id)

        if not all_info_tree:
            raise HTTPException(status_code=404, detail="Main Board not found")

        return all_info_tree
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/{main_board_id}", response_model=MainBoard)
async def get_main_board(main_board_id: int, client_user_id: int, token: str = Depends(verify_token)):
    try:
        main_board = main_board_repository.get_main_board(main_board_id, client_user_id)
        if not main_board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main Board not found")
        return main_board
    except HTTPException as e:
        raise e

@router.put("/{main_board_id}", response_model=MainBoard)
async def update_main_board(main_board_id: int, main_board: MainBoard, client_user_id: int, token: str = Depends(verify_token)):
    try:
        updated_main_board = main_board_repository.update_main_board(main_board_id, main_board, client_user_id)
        if not updated_main_board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main Board not found")
        return updated_main_board
    except HTTPException as e:
        raise e

@router.delete("/{main_board_id}", response_model=MainBoard)
async def delete_main_board(main_board_id: int, client_user_id: int, token: str = Depends(verify_token)):
    try:
        deleted_main_board = main_board_repository.delete_main_board(main_board_id, client_user_id)
        if not deleted_main_board:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main Board not found")
        return deleted_main_board
    except HTTPException as e:
        raise e
    
@router.delete("/main_board_delete_cascade/{main_board_id}", response_model=dict, tags=["Main Boards"])
def delete_main_board_cascade(main_board_id: int,  db: Session = Depends(get_db)):
    try:
        main_board = db.query(MainBoard).filter(MainBoard.id == main_board_id).first()

        if not main_board:
            raise HTTPException(status_code=404, detail="Main board not found")

        # ✅ 1. Delete related MainBoardAccess records
        db.execute(
            text("DELETE FROM \"MainBoardAccess\" WHERE main_board_id = :main_board_id"),
            {"main_board_id": main_board_id}
        )

        # ✅ 2. Delete related BoardAccess records first
        db.execute(
            text("DELETE FROM \"BoardAccess\" WHERE board_id IN (SELECT id FROM \"Boards\" WHERE main_board_id = :main_board_id)"),
            {"main_board_id": main_board_id}
        )

        # ✅ 3. Delete related Boards before deleting MainBoard
        db.query(Boards).filter(Boards.main_board_id == main_board_id).delete(synchronize_session=False)

        # ✅ 4. Now delete the MainBoard
        db.delete(main_board)
        db.commit()

        return {"message": "Main board and associated records deleted successfully"}
    
    except SQLAlchemyError as e:
        db.rollback()
        print(f"SQLAlchemy Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")