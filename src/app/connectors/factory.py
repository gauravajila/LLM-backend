# connectors/factory.py
from typing import Dict
from app.connectors.database_connector import DatabaseConnector
from app.connectors.cloud_storage_connector import CloudStorageConnector

class ConnectorFactory:
    @staticmethod
    def create_connector(source_type: str, config: Dict):
        if source_type == "database":
            return DatabaseConnector(config)
        elif source_type == "cloud_storage":
            return CloudStorageConnector(config["provider"], config["credentials"])
        else:
            raise ValueError(f"Unsupported source type: {source_type}")