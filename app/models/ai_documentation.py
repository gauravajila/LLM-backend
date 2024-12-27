# app/models/ai_documentation.py
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel

class AiDocumentation(BaseModel):
    id: Optional[Any] = None
    board_id: int
    configuration_details: Optional[str] = None
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "board_id": 1,
                    "name": "AI Documentation",
                    "configuration_details":'{"Key":"Value"}'
                }
            ]
        }