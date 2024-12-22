# models/permissions.py
from enum import Enum

class MainBoardPermission(Enum):
    VIEW = "view"
    EDIT = "edit"
    DELETE = "delete"
    CREATE = "create"