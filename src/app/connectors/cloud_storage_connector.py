# connectors/cloud_storage_connector.py
import logging
from google.cloud import storage
import boto3
from azure.storage.blob import BlobServiceClient
import pandas as pd
import io
from .base import DataConnector
from typing import Dict, List

class CloudStorageConnector(DataConnector):
    def __init__(self, provider: str, credentials: Dict):
        self.provider = provider.lower()
        self.credentials = credentials
        self.client = None
        self.logger = logging.getLogger(__name__)
        self._validate_provider()
    
    def _validate_provider(self):
        valid_providers = ['gcs', 's3', 'azure']
        if self.provider not in valid_providers:
            raise ValueError(f"Unsupported cloud provider. Must be one of: {valid_providers}")
    
    def connect(self) -> bool:
        try:
            if self.provider == "gcs":
                self.client = storage.Client.from_service_account_info(self.credentials)
            elif self.provider == "s3":
                self.client = boto3.client('s3', **self.credentials)
            elif self.provider == "azure":
                self.client = BlobServiceClient.from_connection_string(
                    self.credentials['connection_string']
                )
            return self.validate_connection()
        except Exception as e:
            self.logger.error(f"Cloud storage connection failed: {str(e)}")
            raise ConnectionError(f"Failed to connect to {self.provider}: {str(e)}")
    
    def validate_connection(self) -> bool:
        try:
            if self.provider == "gcs":
                next(iter(self.client.list_buckets()))
            elif self.provider == "s3":
                self.client.list_buckets()
            elif self.provider == "azure":
                next(iter(self.client.list_containers()))
            return True
        except Exception as e:
            self.logger.error(f"Connection validation failed: {str(e)}")
            raise ConnectionError(f"Connection validation failed: {str(e)}")
    
    def list_available_sources(self, location: str) -> List[Dict]:
        try:
            if self.provider == "gcs":
                return self._list_gcs_files(location)
            elif self.provider == "s3":
                return self._list_s3_files(location)
            elif self.provider == "azure":
                return self._list_azure_files(location)
        except Exception as e:
            self.logger.error(f"Failed to list files: {str(e)}")
            raise RuntimeError(f"Failed to list files: {str(e)}")
    
    def _list_gcs_files(self, bucket_name: str) -> List[Dict]:
        bucket = self.client.bucket(bucket_name)
        return [
            {
                "name": blob.name,
                "size": blob.size,
                "updated": blob.updated,
                "content_type": blob.content_type
            } for blob in bucket.list_blobs()
        ]
    
    def _list_s3_files(self, bucket_name: str) -> List[Dict]:
        response = self.client.list_objects_v2(Bucket=bucket_name)
        return [
            {
                "name": obj['Key'],
                "size": obj['Size'],
                "updated": obj['LastModified'],
                "content_type": obj.get('ContentType', '')
            } for obj in response.get('Contents', [])
        ]
    
    def _list_azure_files(self, container_name: str) -> List[Dict]:
        container_client = self.client.get_container_client(container_name)
        return [
            {
                "name": blob.name,
                "size": blob.size,
                "updated": blob.last_modified,
                "content_type": blob.content_settings.content_type
            } for blob in container_client.list_blobs()
        ]
    
    def retrieve_data(self, file_paths: List[str], location: str) -> Dict[str, pd.DataFrame]:
        data = {}
        try:
            for file_path in file_paths:
                content = self._get_file_content(location, file_path)
                if file_path.lower().endswith('.csv'):
                    data[file_path] = pd.read_csv(io.BytesIO(content))
                elif file_path.lower().endswith('.parquet'):
                    data[file_path] = pd.read_parquet(io.BytesIO(content))
                else:
                    raise ValueError(f"Unsupported file format: {file_path}")
            return data
        except Exception as e:
            self.logger.error(f"Failed to retrieve data: {str(e)}")
            raise RuntimeError(f"Failed to retrieve data: {str(e)}")
    
    def _get_file_content(self, location: str, file_path: str) -> bytes:
        try:
            if self.provider == "gcs":
                bucket = self.client.bucket(location)
                blob = bucket.blob(file_path)
                return blob.download_as_bytes()
            elif self.provider == "s3":
                response = self.client.get_object(Bucket=location, Key=file_path)
                return response['Body'].read()
            elif self.provider == "azure":
                blob_client = self.client.get_blob_client(
                    container=location, blob=file_path
                )
                return blob_client.download_blob().readall()
        except Exception as e:
            self.logger.error(f"Failed to get file content: {str(e)}")
            raise RuntimeError(f"Failed to get file content: {str(e)}")