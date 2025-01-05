# app/models/prompt.py
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class PromptBase(SQLModel):
    prompt_text: str
    prompt_out: str
    client_number: Optional[str] = None
    customer_number: Optional[str] = None

class PromptCreate(PromptBase):
    board_id: int
    user_name: Optional[str] = None

class Prompt(SQLModel, table=True):
    __tablename__ = "Prompts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    board_id: int = Field(foreign_key="Boards.id")
    prompt_text: str
    prompt_out: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    user_name: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "examples": [
                {
                    "board_id": 17,
                    "prompt_text": "test string",
                    "prompt_out": "out string",
                    "user_name": "Shashi Raj"
                }
            ]
        }
