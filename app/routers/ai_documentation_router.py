# app/routers/ai_documentation_router.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.repositories.ai_documentation_repository import AiDocumentationRepository
from app.models.ai_documentation import AiDocumentation

router = APIRouter(prefix="/ai-documentation", tags=["AI Documentation"])

ai_documentation_repository = AiDocumentationRepository()

@router.post("/", response_model=AiDocumentation)
async def create_ai_documentation(ai_documentation: AiDocumentation):
    try:
        # Attempt to create AI Documentation
        created_documentation = ai_documentation_repository.create_ai_documentation(ai_documentation)
        return created_documentation
    except Exception as e:
        # Check if the error is due to a duplicate key violation
        if "duplicate key value violates unique constraint" in str(e):
            raise HTTPException(status_code=400, detail="AI Documentation Under this Board already exist")
        else:
            # Re-raise the exception if it's not related to duplicate key violation
            raise HTTPException(status_code=500, detail="AI Documentation API Fails to process")

@router.get("/", response_model=List[AiDocumentation])
async def get_all_ai_documentation():
    all_documentation = ai_documentation_repository.get_all_ai_documentation()
    return all_documentation

@router.get("/{doc_id}", response_model=AiDocumentation)
async def get_ai_documentation(doc_id: int):
    documentation = ai_documentation_repository.get_ai_documentation(doc_id)
    if not documentation:
        raise HTTPException(status_code=404, detail="AI Documentation not found")
    return documentation

@router.put("/{doc_id}", response_model=AiDocumentation)
async def update_ai_documentation(doc_id: int, ai_documentation: AiDocumentation):
    updated_documentation = ai_documentation_repository.update_ai_documentation(doc_id, ai_documentation)
    if not updated_documentation:
        raise HTTPException(status_code=404, detail="AI Documentation not found")
    return updated_documentation

@router.delete("/{doc_id}", response_model=dict)
async def delete_ai_documentation(doc_id: int):
    deleted_documentation = ai_documentation_repository.delete_ai_documentation(doc_id)
    if not deleted_documentation:
        raise HTTPException(status_code=404, detail="AI Documentation not found")
    response_data = {"status_code": 200, "detail": "AI Documentation deleted successfully"}
    return response_data