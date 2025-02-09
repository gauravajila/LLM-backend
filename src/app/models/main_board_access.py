# models/main_board_access.py
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from app.models.main_board import MainBoard

class MainBoardAccess(SQLModel, table=True):
    __tablename__ = "MainBoardAccess"
    
    # id: Optional[int] = Field(default=None, primary_key=True)
    main_board_id: int = Field(foreign_key="MainBoard.id", primary_key=True)
    client_user_id: int = Field(foreign_key="ClientUsers.id", primary_key=True)
    permission: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    main_board: Optional["MainBoard"] = Relationship(back_populates="accesses")  # Use forward declaration