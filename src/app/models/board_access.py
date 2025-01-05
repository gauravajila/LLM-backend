# models/board_access.py
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from app.models.boards import Boards

class BoardAccess(SQLModel, table=True):
    __tablename__ = "BoardAccess"
    
    board_id: int = Field(foreign_key="Boards.id", primary_key=True)
    client_user_id: int = Field(foreign_key="ClientUsers.id", primary_key=True)
    permission: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    board: Boards = Relationship(back_populates="accesses")