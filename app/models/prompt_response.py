# app/models/prompt_response.py
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Json

class PromptResponse(BaseModel):
    id: Optional[Any] = None
    board_id: int
    prompt_text: str
    prompt_out: Json
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    hash_key: str

    class Config:
        orm_mode = True
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