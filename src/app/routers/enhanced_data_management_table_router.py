from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional
from app.models.data_management_table import DataManagementTable, TableStatus
from app.repositories.enhanced_data_management_repository import EnhancedDataManagementRepository
from app.connectors.factory import ConnectorFactory

router = APIRouter(prefix="/main-boards/boards", tags=["Enhanced Data Management Tables"])

@router.post("/database/tables", response_model=List[DataManagementTable])
async def create_tables_from_database(
    board_id: int,
    connection_config: Dict,
    selected_tables: List[str],
    description: Optional[str] = ""
):
    try:
        repository = EnhancedDataManagementRepository()
        return repository.create_table_from_database(
            board_id, connection_config, selected_tables, description
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cloud-storage/tables", response_model=List[DataManagementTable])
async def create_tables_from_cloud_storage(
    board_id: int,
    storage_config: Dict,
    location: str,
    selected_files: List[str],
    description: Optional[str] = ""
):
    try:
        repository = EnhancedDataManagementRepository()
        return repository.create_table_from_cloud_storage(
            board_id, storage_config, location, selected_files, description
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Utility routes for source discovery remain the same as in previous implementation
@router.post("/database/test-connection")
async def test_database_connection(connection_config: Dict):
    # try:
    connector = ConnectorFactory.create_connector("database", connection_config)
    return {"success": connector.connect()}
    # except Exception as e:
    #     raise HTTPException(status_code=400, detail=str(e))

@router.get("/database/available-tables")
async def list_database_tables(connection_config: Dict):
    try:
        connector = ConnectorFactory.create_connector("database", connection_config)
        connector.connect()
        return connector.list_available_sources()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cloud-storage/test-connection")
async def test_cloud_storage_connection(storage_config: Dict):
    try:
        connector = ConnectorFactory.create_connector("cloud_storage", storage_config)
        return {"success": connector.connect()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/cloud-storage/available-files")
async def list_cloud_storage_files(storage_config: Dict, location: str):
    try:
        connector = ConnectorFactory.create_connector("cloud_storage", storage_config)
        connector.connect()
        return connector.list_available_sources(location)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))