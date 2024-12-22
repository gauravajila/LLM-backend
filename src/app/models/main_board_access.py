# models/main_board_access.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class MainBoardAccess:
    id: Optional[int]
    main_board_id: int
    client_user_id: int
    permission: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None