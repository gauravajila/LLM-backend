# app/models/boards.py
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class Boards(SQLModel, table=True):
    __tablename__ = "Boards"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    main_board_id: int = Field(foreign_key="MainBoard.id")
    name: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "main_board_id": 1,
                    "name": "Sale Analysis",
                }
            ]
        }