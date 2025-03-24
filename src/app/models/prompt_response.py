# app/models/prompt_response.py
from datetime import datetime
from typing import Optional, Any, Dict
from sqlmodel import SQLModel, Field, JSON, Column, ForeignKey, Relationship
from pydantic import Json

class PromptResponseBase(SQLModel):
    board_id: int = Field(sa_column=Column(ForeignKey("Boards.id", ondelete="CASCADE")))
    prompt_text: str
    prompt_out: Dict = Field(sa_type=JSON)
    hash_key: str

class PromptResponse(PromptResponseBase, table=True):
    __tablename__ = "PromptsResponse"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    board: Optional["Boards"] = Relationship(back_populates="prompts_responses")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "board_id": 1,
                    "prompt_text": "Example prompt text",
                    "prompt_out": "Example prompt output",
                    "hash_key": "example_hash_key"
                }
            ]
        }