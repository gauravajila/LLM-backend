# app/models/data_management_table.py
# app/models/data_management_table.py
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, JSON
from pydantic import ConfigDict

class DataManagementTableBase(SQLModel):
    board_id: Optional[int] = Field(default=None, foreign_key="Boards.id")
    table_name: str = Field(index=True)
    table_description: Optional[str] = Field(default=None)
    table_column_type_detail: Optional[dict] = Field(default=None, sa_type=JSON)

class DataManagementTable(DataManagementTableBase, table=True):
    __tablename__ = "DataManagementTable"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "table_name": "SalesData",
                    "table_description": "Monthly sales data",
                    "board_id": 1,
                    "table_column_type_detail": {"info": 1},
                }
            ]
        }
    )

class TableStatusBase(SQLModel):
    data_management_table_id: Optional[int] = Field(
        default=None, foreign_key="DataManagementTable.id"
    )
    month_year: str = Field(index=True)
    approved: bool = Field(default=False)
    filename: str
    file_download_link: Optional[str] = None

class TableStatus(TableStatusBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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