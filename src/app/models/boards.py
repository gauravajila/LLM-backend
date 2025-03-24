# app/models/boards.py
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.orm import relationship
from typing import List
from app.models.prompt import Prompt

class Boards(SQLModel, table=True):
    __tablename__ = "Boards"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    # main_board_id: int = Field(foreign_key="MainBoard.id") 
    name: str
    main_board_id: Optional[int] = Field(default=None, foreign_key="MainBoard.id")  # Ensure ForeignKey exists
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    main_board: Optional["MainBoard"] = Relationship(back_populates="boards")

    # Add relationship to board access
    #Gaurav Changes: added the 'sa_relationship_kwargs={"cascade": "all, delete-orphan"}'  
    accesses: List["BoardAccess"] = Relationship(
        back_populates="board",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    ai_docs: List["AiDocumentation"] = Relationship(
        back_populates="board",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    prompts: List["Prompt"] = Relationship(
        back_populates="board",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    # prompts_responses: List["PromptResponse"] = Relationship(
    #     back_populates="board", 
    #     cascade="all, delete"
    # )
    prompts_responses: List["PromptResponse"] = Relationship(
        back_populates="board", 
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    #Gaurav Changes
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "main_board_id": 1,
                    "name": "Sale Analysis",
                }
            ]
        }