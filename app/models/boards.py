# app/models/boards.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base  # Import Base from database.py

class Boards(Base):
    __tablename__ = "boards"  # Define table name

    id = Column(Integer, primary_key=True, index=True)
    main_board_id = Column(Integer, ForeignKey('main_boards.id'), nullable=False)  # Foreign key to MainBoard
    name = Column(String, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with MainBoard
    main_board = relationship("MainBoard", back_populates="boards")

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "main_board_id": 1,
                    "name": "Sale Analysis",
                    "is_active": True
                }
            ]
        }
