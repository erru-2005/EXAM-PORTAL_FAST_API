from fastapi import APIRouter

from app.api.v1.endpoints import hello, administrator, student

api_router = APIRouter()
api_router.include_router(hello.router, prefix="/hello", tags=["hello"])
api_router.include_router(administrator.router, prefix="/administrator", tags=["administrator"])
api_router.include_router(student.router, prefix="/student", tags=["student"])
