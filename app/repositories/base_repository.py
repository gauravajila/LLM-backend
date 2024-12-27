# app/repositories/base_repository.py

from typing import Any, Optional
from psycopg2 import sql
from app.database import get_database_connection

class BaseRepository:
    def __init__(self, table_name: str):
        self.table_name = table_name

    def execute_query_aws(self, query: sql.SQL, values: Optional[tuple] = None) -> Any:
        connection = get_database_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, values)
                result = cursor.fetchone()
            connection.commit()
        finally:
            connection.close()
        return result
    
    def execute_query_all_aws(self, query: sql.SQL, values: Optional[tuple] = None) -> Any:
        connection = get_database_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, values)
                result = cursor.fetchall()
            connection.commit()
        finally:
            connection.close()
        return result

    def execute_query(self, query: sql.SQL, values: Optional[tuple] = None) -> Any:
        connection = get_database_connection()
        try:
            with connection.connect() as cursor:
                out = cursor.execute(query, values)
                result = out.fetchone()
                cursor.commit()
        finally:
            connection.dispose()
        return result
    
    def execute_query_all(self, query: sql.SQL, values: Optional[tuple] = None) -> Any:
        connection = get_database_connection()
        try:
            with connection.connect() as cursor:
                out = cursor.execute(query, values)
                result = out.fetchall()
                cursor.commit()
        finally:
            connection.dispose()
        return result
    
    def create_table(self, query: sql.SQL, values: Optional[tuple] = None) -> Any:
        connection = get_database_connection()
        try:
            with connection.connect() as cursor:
                out = cursor.execute(query, values)
                cursor.commit()
        finally:
            connection.dispose()