# main.py

import uvicorn
import os

from fastapi import FastAPI
from app.routers import (client_user_router, main_board_router,board_router , prompt_router ,data_management_table_router, ai_documentation_router)
                       
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
origins = ["*", "http://localhost:3000"]#,"https://prospero-two.vercel.app","http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(client_user_router.router, tags=["Client Users"])
app.include_router(main_board_router.router, tags=["Main Boards"])
app.include_router(board_router.router, prefix="/main-boards", tags=["Boards"])
app.include_router(prompt_router.router, prefix="/main-boards/boards", tags=["Prompts"])
app.include_router(data_management_table_router.router, prefix="/main-boards/boards", tags=["Data Management Tables"])
app.include_router(ai_documentation_router.router, prefix="/main-boards/boards", tags=["AI Documentation"])
# app.include_router(time_line_settings_router.router, prefix="/main-boards/boards", tags=["Time Line Settings"])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)