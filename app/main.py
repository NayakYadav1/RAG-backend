from fastapi import FastAPI

from app.api.routes.documents import router as documents_router


app = FastAPI(title="Palm Mind RAG Backend")
app.include_router(documents_router)