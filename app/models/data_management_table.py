# app/models/data_management_table.py
from datetime import datetime
from typing import Optional, Any, Text
from pydantic import BaseModel, Json

class DataManagementTable(BaseModel):
    id: Optional[Any] = None
    board_id: Optional[Any]
    table_name: str
    table_description: Optional[Text]
    table_column_type_detail: Optional[Text]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "table_name": "SalesData",
                    "table_description": "Monthly sales data",
                    "board_id": 1,  # Change from "1" to None
                    "table_column_type_detail": '{"info": 1}',
                }
            ]
        }

class TableStatus(BaseModel):
    id: Optional[int] = None
    data_management_table_id: Optional[int] = None
    month_year: str
    approved: bool
    filename: str
    file_download_link: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_schema_extra = {
            "examples": [
                {
                    "data_management_table_table_name": "SalesData",
                    "month_year":"12024",
                    "approved":False,
                    "filename":"sales_data_12024.csv",
                    "file_download_link":"test.download/sales_data_12024.csv"
                }
            ]
        }