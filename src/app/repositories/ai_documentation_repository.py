# app/repositories/ai_documentation_repository.py
from typing import List, Optional
from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.ai_documentation import AiDocumentation
from app.database import engine

class AiDocumentationRepository:
    def __init__(self):
        self.engine = engine
        AiDocumentation.metadata.create_all(self.engine)

    def create_ai_documentation(self, ai_documentation: AiDocumentation) -> AiDocumentation:
        with Session(self.engine) as session:
            db_doc = AiDocumentation(
                board_id=ai_documentation.board_id,
                configuration_details=ai_documentation.configuration_details,
                name=ai_documentation.name
            )
            session.add(db_doc)
            session.commit()
            session.refresh(db_doc)
            return db_doc

    def get_all_ai_documentation(self) -> List[AiDocumentation]:
        with Session(self.engine) as session:
            statement = select(AiDocumentation)
            results = session.exec(statement).all()
            for doc in results:
                try:
                    doc.configuration_details = eval(doc.configuration_details)
                except Exception:
                    pass
            return results

    def get_ai_documentation(self, doc_id: int) -> Optional[AiDocumentation]:
        with Session(self.engine) as session:
            statement = select(AiDocumentation).where(AiDocumentation.id == doc_id)
            doc = session.exec(statement).first()
            if doc:
                try:
                    doc.configuration_details = eval(doc.configuration_details)
                except Exception:
                    pass
            return doc

    def update_ai_documentation(self, doc_id: int, ai_documentation: AiDocumentation) -> Optional[AiDocumentation]:
        with Session(self.engine) as session:
            db_doc = session.get(AiDocumentation, doc_id)
            if not db_doc:
                return None
            
            update_data = ai_documentation.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_doc, key, value)
            
            session.add(db_doc)
            session.commit()
            session.refresh(db_doc)
            return db_doc

    def delete_ai_documentation(self, doc_id: int) -> Optional[AiDocumentation]:
        with Session(self.engine) as session:
            db_doc = session.get(AiDocumentation, doc_id)
            if not db_doc:
                return None
            
            session.delete(db_doc)
            session.commit()
            return db_doc

    def update_ai_documentation_for_board(self, board_id: int, ai_documentation: AiDocumentation) -> Optional[AiDocumentation]:
        """
        Update AI documentation for a specific board.

        Args:
            board_id (int): The ID of the board for which AI documentation needs to be updated.
            ai_documentation (AiDocumentation): The AI documentation object containing updated information.

        Returns:
            Optional[AiDocumentation]: Updated AI documentation instance if successful, otherwise None.
        """
        with Session(self.engine) as session:
            statement = select(AiDocumentation).where(AiDocumentation.board_id == board_id)
            existing_doc = session.exec(statement).first()
            
            if existing_doc:
                return self._update_existing_ai_documentation(board_id, ai_documentation)
            else:
                return self.create_ai_documentation(ai_documentation)

    def _update_existing_ai_documentation(self, board_id: int, ai_documentation: AiDocumentation) -> Optional[AiDocumentation]:
        """
        Update existing AI documentation.

        Args:
            board_id (int): The ID of the board for which AI documentation needs to be updated.
            ai_documentation (AiDocumentation): The AI documentation object containing updated information.

        Returns:
            Optional[AiDocumentation]: Updated AI documentation instance if successful, otherwise None.
        """
        with Session(self.engine) as session:
            statement = select(AiDocumentation).where(AiDocumentation.board_id == board_id)
            db_doc = session.exec(statement).first()
            if not db_doc:
                return None

            db_doc.configuration_details = ai_documentation.configuration_details
            db_doc.name = ai_documentation.name
            
            session.add(db_doc)
            session.commit()
            session.refresh(db_doc)
            return db_doc