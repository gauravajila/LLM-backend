# connectors/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd

class DataConnector(ABC):
    """Base abstract class for all data connectors"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the data source"""
        pass
    
    @abstractmethod
    def list_available_sources(self) -> List[Dict]:
        """List available data sources"""
        pass
    
    @abstractmethod
    def retrieve_data(self, source_identifiers: List[str]) -> Dict[str, pd.DataFrame]:
        """Retrieve data from specified sources"""
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate connection parameters"""
        pass