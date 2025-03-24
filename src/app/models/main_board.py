# app/models/main_board.py
# #ANALYSIS  FORECASTING KPI_DEFINITION WHAT_IF_FRAMEWORK PROFITABILITY_ANALYSIS
from datetime import datetime
from typing import Optional, List
# from app.models.main_board_access import MainBoardAccess
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.orm import relationship
from app.models.boards import Boards


class MainBoard(SQLModel, table=True):
    __tablename__ = "MainBoard"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    client_user_id: Optional[int] = Field(foreign_key="ClientUsers.id")
    name: str
    main_board_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    accesses: List["MainBoardAccess"] = Relationship(
        back_populates="main_board",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True}
    )

    # ✅ Enable cascade delete for Boards
    boards: List["Boards"] = Relationship(
        back_populates="main_board",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "passive_deletes": True}
    )
    #changes by gaurav

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "client_user_id": 1,
                    "name": "Analysis",
                    "main_board_type": "ANALYSIS"
                }
            ]
        }