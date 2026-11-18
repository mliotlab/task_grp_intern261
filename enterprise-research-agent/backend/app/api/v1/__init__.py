from fastapi import APIRouter

from app.api.v1 import auth, collections, documents, research

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(collections.router)
api_router.include_router(documents.router)
api_router.include_router(research.router)
