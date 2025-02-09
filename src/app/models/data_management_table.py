from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON, Relationship
from sqlalchemy import Column, Integer, ForeignKey
from pydantic import ConfigDict

class DataManagementTableBase(SQLModel):
    board_id: Optional[int] = Field(default=None, foreign_key="Boards.id")
    table_name: str = Field(index=True)
    table_description: Optional[str] = Field(default=None)
    table_column_type_detail: str = Field(default=None)

class DataManagementTable(DataManagementTableBase, table=True):
    __tablename__ = "DataManagementTable"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Define the relationship to TableStatus
    table_statuses: List["TableStatus"] = Relationship(
        back_populates="data_management_table",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "table_name": "SalesData",
                    "table_description": "Monthly sales data",
                    "board_id": 1,
                    "table_column_type_detail": "",
                }
            ]
        }
    )

class TableStatusBase(SQLModel):
    # Use only sa_column for foreign key
    data_management_table_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("DataManagementTable.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    month_year: str = Field(index=True)
    approved: bool = Field(default=False)
    filename: str
    file_download_link: Optional[str] = None

class TableStatus(TableStatusBase, table=True):
    __tablename__ = "tablestatus"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Define the relationship back to DataManagementTable
    data_management_table: DataManagementTable = Relationship(back_populates="table_statuses")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "data_management_table_table_name": "SalesData",
                    "month_year": "12024",
                    "approved": False,
                    "filename": "sales_data_12024.csv",
                    "file_download_link": "test.download/sales_data_12024.csv"
                }
            ]
        }
    )