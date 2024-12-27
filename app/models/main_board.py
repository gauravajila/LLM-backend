# app/models/main_board.py
from datetime import datetime
from typing import Optional, List
from app.models.boards import Boards
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base  # Import Base from database.py

class MainBoard(Base):
    __tablename__ = "main_boards"  # Define table name

    id = Column(Integer, primary_key=True, index=True)
    client_user_id = Column(Integer, nullable=True)
    name = Column(String, index=True)  # ANALYSIS, FORECASTING, KPI_DEFINITION, WHAT_IF_FRAMEWORK, PROFITABILITY_ANALYSIS
    main_board_type = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    boards: Optional[List["Boards"]] = []  # Define the relationship to the Boards model

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "client_user_id": 1,
                    "name": "Analysis",
                    "main_board_type": "ANALYSIS"
                }
            ]
        }
