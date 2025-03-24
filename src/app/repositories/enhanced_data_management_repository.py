#repositories/enhanced_data_management_repository.py
from typing import Dict, List, Optional
from app.repositories.data_management_table_repository import DataManagementTableRepository, TableStatusRepository
from app.models.data_management_table import DataManagementTable, TableStatus
from app.connectors.factory import ConnectorFactory
from datetime import datetime
import pandas as pd
import json

class EnhancedDataManagementRepository(DataManagementTableRepository):
    def __init__(self):
        super().__init__()
        self.table_status_repo = TableStatusRepository()
        self.connector_factory = ConnectorFactory()

    def create_table_from_database(
        self,
        board_id: int,
        connection_config: Dict,
        selected_tables: List[str],
        description: str = ""
    ) -> List[DataManagementTable]:
        """
        Create DataManagementTable entries from database tables and import their data
        """
        try:
            # Create database connector
            connector = self.connector_factory.create_connector("database", connection_config)
            connector.connect()

            created_tables = []
            
            # Get data and schema for each selected table
            for table_name in selected_tables:
                # Get table schema
                schema = self._get_table_schema(connector, table_name)
                
                # Create DataManagementTable entry
                table_data = {
                    "board_id": board_id,
                    "table_name": table_name,
                    "table_description": description,
                    "table_column_type_detail": json.dumps(schema)
                }
                data_management_table = DataManagementTable(**table_data)
                
                # Save to database
                created_table = self.create_data_management_table(data_management_table)
                created_tables.append(created_table)
                
                # Import the data
                data = connector.retrieve_data([table_name])
                df = data[table_name]
                
                # Create TableStatus entry and upload data
                current_month = datetime.now().strftime("%Y-%m")
                table_status = TableStatus(
                    data_management_table_id=created_table.id,
                    month_year=current_month,
                    approved=False,
                    filename=f"{table_name}_{current_month}.csv"
                )
                
                self.table_status_repo.upload_file_table_status(df, table_status)
            
            return created_tables
            
        except Exception as e:
            raise RuntimeError(f"Failed to create table from database: {str(e)}")

    def _get_table_schema(self, connector, table_name: str) -> Dict:
        """Get schema information for a database table"""
        query = f"""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = :table_name;
        """
        with connector.engine.connect() as conn:
            result = conn.execute(text(query), {"table_name": table_name})
            schema = {
                row[0]: {
                    "type": row[1],
                    "length": row[2]
                } for row in result
            }
            return schema

    def create_table_from_cloud_storage(
        self,
        board_id: int,
        storage_config: Dict,
        location: str,
        selected_files: List[str],
        description: str = ""
    ) -> List[DataManagementTable]:
        """
        Create DataManagementTable entries from cloud storage files and import their data
        """
        try:
            # Create cloud storage connector
            connector = self.connector_factory.create_connector("cloud_storage", storage_config)
            connector.connect()
            
            created_tables = []
            
            # Get data for each selected file
            data = connector.retrieve_data(selected_files, location)
            
            for file_name, df in data.items():
                # Infer schema from DataFrame
                schema = self._infer_schema_from_dataframe(df)
                
                # Create DataManagementTable entry
                table_name = file_name.split('.')[0]  # Remove file extension
                table_data = {
                    "board_id": board_id,
                    "table_name": table_name,
                    "table_description": description,
                    "table_column_type_detail": json.dumps(schema)
                }
                data_management_table = DataManagementTable(**table_data)
                
                # Save to database
                created_table = self.create_data_management_table(data_management_table)
                created_tables.append(created_table)
                
                # Create TableStatus entry and upload data
                current_month = datetime.now().strftime("%Y-%m")
                table_status = TableStatus(
                    data_management_table_id=created_table.id,
                    month_year=current_month,
                    approved=False,
                    filename=f"{table_name}_{current_month}.csv"
                )
                
                self.table_status_repo.upload_file_table_status(df, table_status)
            
            return created_tables
            
        except Exception as e:
            raise RuntimeError(f"Failed to create table from cloud storage: {str(e)}")

    def _infer_schema_from_dataframe(self, df: pd.DataFrame) -> Dict:
        """Infer schema from pandas DataFrame"""
        schema = {}
        for column in df.columns:
            dtype = str(df[column].dtype)
            schema[column] = {
                "type": self._map_pandas_type_to_sql(dtype),
                "length": None
            }
        return schema

    def _map_pandas_type_to_sql(self, pandas_type: str) -> str:
        """Map pandas data types to SQL data types"""
        type_mapping = {
            'object': 'VARCHAR',
            'int64': 'INTEGER',
            'float64': 'FLOAT',
            'datetime64[ns]': 'TIMESTAMP',
            'bool': 'BOOLEAN',
        }
        return type_mapping.get(pandas_type, 'VARCHAR')