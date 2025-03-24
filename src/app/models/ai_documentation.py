# app/models/ai_documentation.py
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from pydantic import validator

class AiDocumentation(SQLModel, table=True):
    __tablename__ = "AiDocumentation"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    board_id: int = Field(foreign_key="Boards.id")
    configuration_details: Optional[str] = None
    name: str
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    board: Optional["Boards"] = Relationship(back_populates="ai_docs")

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "board_id": 1,
                    "name": "AI Documentation",
                    "configuration_details": '{"Key":"Value"}'
                }
            ]
        }

    @validator("updated_at", pre=True, always=True)
    def set_updated_at(cls, v, values, **kwargs):
        return datetime.utcnow()