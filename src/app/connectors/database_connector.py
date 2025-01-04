from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List
import pandas as pd
from app.connectors.base import DataConnector
import logging


class DatabaseConnector(DataConnector):
    def __init__(self, connection_params: Dict):
        """
        Initialize database connector.
        
        Args:
            connection_params (Dict): {
                'host': str,
                'port': int,
                'database': str,
                'user': str,
                'password': str
            }
        """
        self.connection_params = connection_params
        self.engine = None
        self.logger = logging.getLogger(__name__)
    
    def _build_connection_string(self) -> str:
        """
        Build the PostgreSQL connection string.
        
        Returns:
            str: The PostgreSQL connection string.
        """
        return f"postgresql://{self.connection_params['user']}:{self.connection_params['password']}@" \
               f"{self.connection_params['host']}:{self.connection_params['port']}/{self.connection_params['database']}"
    
 
    def connect(self) -> bool:
        """
        Establish a connection to the PostgreSQL database.
        
        Returns:
            bool: True if the connection is successful.
        
        Raises:
            ConnectionError: If the connection fails.
        """
        try:
            connection_string = self._build_connection_string()
            self.engine = create_engine(connection_string)
            return self.validate_connection()
        except SQLAlchemyError as e:
            self.logger.error(f"Database connection failed: {str(e)}")
            raise ConnectionError(f"Failed to connect to database: {str(e)}")
    
    def validate_connection(self) -> bool:
        """
        Validate the database connection by executing a simple query.
        
        Returns:
            bool: True if the validation query succeeds.
        
        Raises:
            ConnectionError: If the validation query fails.
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as e:
            self.logger.error(f"Connection validation failed: {str(e)}")
            raise ConnectionError(f"Connection validation failed: {str(e)}")
    
    def list_available_sources(self) -> List[Dict]:
        """
        List all available tables and their metadata.
        
        Returns:
            List[Dict]: A list of dictionaries containing table metadata.
        
        Raises:
            RuntimeError: If the query fails.
        """
        query = """
            SELECT 
                table_schema,
                table_name,
                (SELECT COUNT(*) FROM information_schema.columns 
                 WHERE table_name=tables.table_name) as column_count,
                obj_description((table_schema || '.' || table_name)::regclass, 'pg_class') as table_comment
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name;
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                return [
                    {
                        "schema": row[0],
                        "name": row[1],
                        "column_count": row[2],
                        "description": row[3] or ""
                    } for row in result
                ]
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to list tables: {str(e)}")
            raise RuntimeError(f"Failed to list tables: {str(e)}")
    
    def get_table_schema(self, table_name: str) -> Dict:
        """
        Get the schema of a specific table.
        
        Args:
            table_name (str): The name of the table.
        
        Returns:
            Dict: A dictionary containing the schema details of the table.
        
        Raises:
            RuntimeError: If the query fails.
        """
        query = """
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                column_default,
                is_nullable,
                col_description((table_schema || '.' || table_name)::regclass::oid, ordinal_position) as column_comment
            FROM information_schema.columns
            WHERE table_name = :table_name;
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"table_name": table_name})
                return {
                    row[0]: {
                        "type": row[1],
                        "length": row[2],
                        "default": row[3],
                        "nullable": row[4] == 'YES',
                        "description": row[5] or ""
                    } for row in result
                }
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get table schema: {str(e)}")
            raise RuntimeError(f"Failed to get table schema: {str(e)}")
    
    def retrieve_data(self, table_names: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Retrieve data from specified tables.
        
        Args:
            table_names (List[str]): A list of table names to retrieve data from.
        
        Returns:
            Dict[str, pd.DataFrame]: A dictionary with table names as keys and DataFrames as values.
        
        Raises:
            RuntimeError: If data retrieval fails.
        """
        data = {}
        try:
            for table in table_names:
                query = f"SELECT * FROM {table}"
                data[table] = pd.read_sql(query, self.engine)
            return data
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to retrieve data: {str(e)}")
            raise RuntimeError(f"Failed to retrieve data: {str(e)}")
