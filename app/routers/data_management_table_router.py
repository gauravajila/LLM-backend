from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from sqlalchemy.orm import Session
from app.repositories.data_management_table_repository import DataManagementTableRepository, TableStatusRepository
from app.repositories.ai_documentation_repository import AiDocumentationRepository
from app.models.data_management_table import DataManagementTable, TableStatus
from app.models.ai_documentation import AiDocumentation
from typing import List, Optional
from io import BytesIO
import pandas as pd

from fastapi import HTTPException, Depends, Path
from fastapi.responses import FileResponse

from langchain_openai import ChatOpenAI, OpenAI
from app.instructions import get_ai_documentation_instruction
import re
import json

router = APIRouter(prefix="/data-management-table", tags=["Data Management Tables"])

@router.post("/create", response_model=DataManagementTable)
async def create_data_management_table(data_management_table: DataManagementTable):
    repository = DataManagementTableRepository()
    return repository.create_data_management_table(data_management_table)

@router.get("/all", response_model=List[DataManagementTable])
async def get_all_data_management_tables():
    repository = DataManagementTableRepository()
    return repository.get_data_management_tables()

@router.get("/get_all_tables_with_files", response_model=List[dict])
async def get_all_data_management_tables():
    repository = DataManagementTableRepository()
    data_management_tables = repository.get_data_management_tables()
    repository = TableStatusRepository()
    result = []
    for data_table in data_management_tables:
        data_dict = {
            "id": data_table.id,
            "board_id": data_table.board_id,
            "table_name": data_table.table_name,
            "table_description": data_table.table_description,
            "table_column_type_detail": data_table.table_column_type_detail,
            "created_at": data_table.created_at,
            "updated_at": data_table.updated_at,
            "files": []
        }

        # Assuming each data table has a corresponding list of TableStatus instances
        table_statuses =  repository.get_table_statuses_for_data_table(data_table.id)
        for status in table_statuses:
            file_dict = {
                "id": status.id,
                "month_year": status.month_year,
                "approved": status.approved,
                "filename": status.filename,
                "file_download_link": status.file_download_link,
                "created_at": status.created_at,
                "updated_at": status.updated_at
            }
            data_dict["files"].append(file_dict)

        result.append(data_dict)

    return result

@router.get("/get_all_tables_with_files/{data_table_id}", response_model=List[dict])
async def get_data_management_table_with_files(data_table_id: int):
    repository = DataManagementTableRepository()
    data_table = repository.get_data_management_table(data_table_id)

    if not data_table:
        return {"detail": "Data table not found."}

    repository = TableStatusRepository()
    result = {
        "id": data_table.id,
        "board_id": data_table.board_id,
        "table_name": data_table.table_name,
        "table_description": data_table.table_description,
        "table_column_type_detail": data_table.table_column_type_detail,
        "created_at": data_table.created_at,
        "updated_at": data_table.updated_at,
        "files": []
    }

    # Assuming the specified data table has a corresponding list of TableStatus instances
    table_statuses = repository.get_table_statuses_for_data_table(data_table.id)
    for status in table_statuses:
        file_dict = {
            "id": status.id,
            "month_year": status.month_year,
            "approved": status.approved,
            "filename": status.filename,
            "file_download_link": status.file_download_link,
            "created_at": status.created_at,
            "updated_at": status.updated_at
        }
        result["files"].append(file_dict)

    return [result]

#To do Download files API

@router.get("/{table_id}", response_model=DataManagementTable)
async def get_data_management_table(table_id: int):
    repository = DataManagementTableRepository()
    return repository.get_data_management_table(table_id)

@router.put("/{table_id}", response_model=DataManagementTable)
async def update_data_management_table(table_id: int, data_management_table: DataManagementTable):
    repository = DataManagementTableRepository()
    return repository.update_data_management_table(table_id, data_management_table)

@router.delete("/{table_id}", response_model=DataManagementTable)
async def delete_data_management_table(table_id: int):
    repository = DataManagementTableRepository()
    return repository.delete_data_management_table(table_id)

@router.get("/status/all", response_model=List[TableStatus])
async def get_all_table_status():
    repository = TableStatusRepository()
    return repository.get_all_table_status()

@router.get("/status/{table_id}", response_model=Optional[TableStatus])
async def get_table_status_by_id(table_id: int):
    repository = TableStatusRepository()
    return repository.get_table_status_by_id(table_id)

@router.put("/status/approve/{table_id}", response_model=TableStatus)
async def update_approval_status(table_id: int, new_approval_status: bool):
    repository = TableStatusRepository()
    return repository.update_approval_status(table_id, new_approval_status)

@router.post("/status/upload_rag/{data_management_table_id}", response_model=TableStatus)
async def upload_file_to_table_status_for_rag(
    data_management_table_id: int, 
    month_year: str = Form(...),  # Accept month_year as a form field
    file: UploadFile = File(...)):
    status_repository = TableStatusRepository()

    # Read and process the uploaded file
    contents = await file.read()
    buffer = BytesIO(contents)
    # Process the file based on its type if needed
    # For simplicity, let's assume we handle only basic storage here
    # You can add more processing logic based on the file type
    processed_file_data = buffer.getvalue()
    
    # Assuming you want to handle file uploads for a specific table status
    # You can create a new TableStatus instance and save it to the database
    new_table_status = TableStatus(
        data_management_table_id=data_management_table_id,
        month_year=month_year,
        approved=False,
        filename=file.filename,
        file_download_link="",
        created_at=None,  # These fields will be updated by the database
        updated_at=None
        )

    # Save the changes to the database
    updated_table_status = status_repository.upload_file_table_status_for_rag(processed_file_data, new_table_status)
    return updated_table_status


@router.post("/status/upload/{data_management_table_id}", response_model=TableStatus)
async def upload_file_to_table_status(
    data_management_table_id: int, 
    month_year: str = Form(...),  # Accept month_year as a form field
    file: UploadFile = File(...),
    
    #approved: bool = False  # You can customize this default value based on your requirements
):
    status_repository = TableStatusRepository()
    ai_documentation_repository = AiDocumentationRepository()

    # Read and process the uploaded file
    contents = await file.read()
    buffer = BytesIO(contents)
    df = pd.read_csv(buffer)
    buffer.close()
    file.file.close()
    
    # Check if the data for the specified table is already approved
    if status_repository.is_month_data_approved(data_management_table_id, month_year):
        raise HTTPException(status_code=400, detail=f"Data for table {data_management_table_id} and month {month_year} is already approved.")

    # Assuming you want to handle file uploads for a specific table status
    # You can create a new TableStatus instance and save it to the database
    new_table_status = TableStatus(
        data_management_table_id=data_management_table_id,
        month_year=month_year,
        approved=False,
        filename=file.filename,
        file_download_link="",
        created_at=None,  # These fields will be updated by the database
        updated_at=None
    )

    # Save the changes to the database
    updated_table_status = status_repository.upload_file_table_status(df, new_table_status)

    # Create AI Documentation for Board with uploaded data
    board_id = status_repository.get_board_id_for_table_status_id(data_management_table_id)
    llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
    ai_documentation_instruction = get_ai_documentation_instruction()
    config = llm.invoke(ai_documentation_instruction + df.head(2).to_markdown())
    config_output = re.sub(r'\bfalse\b', 'False', re.sub(r'\btrue\b', 'True', config.content, flags=re.IGNORECASE), flags=re.IGNORECASE)
    #Remove special character
    config_output = re.sub(r"```|python|json", "",config_output, 0, re.MULTILINE)
    config_output = eval(config_output)
    config_dict = config_output["configuration_details"]
    config_str = json.dumps(config_dict, indent=2)
    ai_documentation = AiDocumentation(
        board_id=board_id,
        configuration_details=config_str,
        name=file.filename
    )
    created_documentation = ai_documentation_repository.update_ai_documentation_for_board(board_id, ai_documentation)
    #created_documentation = ai_documentation_repository.create_ai_documentation(ai_documentation)
    #We need to add option to submit the files in pub sub with all the details

    return updated_table_status

# @router.get("/status/download/{table_id}", response_model=List[str])
# async def download_files_by_month_year(
#     table_id: int,
#     month_years: Optional[str] = Query(None, description="Month and year in the format 'MMYYYY'.")
#  ):
#     status_repository = TableStatusRepository()
#     output_directory = "src/csv_files"
#     # Ensure the output directory exists
#     Path(output_directory).mkdir(parents=True, exist_ok=True)

#     # Download files and get the list of downloaded file paths
#     downloaded_files = status_repository.download_files_by_month_year(table_id, month_years, output_directory)

#     return downloaded_files

@router.delete("/status/delete/{table_id}", response_model=TableStatus)
async def delete_table_status(table_id: int):
    repository = TableStatusRepository()
    deleted_status = repository.delete_table_status(table_id)
    if not deleted_status:
        raise HTTPException(status_code=404, detail=f"TableStatus with id {table_id} not found")
    return deleted_status
