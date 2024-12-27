# app.exceptions.py
from fastapi import HTTPException

class UserNotFoundException(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="User not found")

class EmailAlreadyInUseException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="Email already in use")

class InternalServerErrorException(HTTPException):
    def __init__(self):
        super().__init__(status_code=500, detail="Internal Server Error")