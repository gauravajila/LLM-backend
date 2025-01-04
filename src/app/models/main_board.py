# app/models/main_board.py
# #ANALYSIS  FORECASTING KPI_DEFINITION WHAT_IF_FRAMEWORK PROFITABILITY_ANALYSIS
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class MainBoard(SQLModel, table=True):
    __tablename__ = "MainBoard"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    client_user_id: Optional[int] = Field(foreign_key="ClientUsers.id")
    name: str
    main_board_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    accesses: List["MainBoardAccess"] = Relationship(back_populates="main_board")
    #boards: List["Board"] = Relationship(back_populates="main_board")

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