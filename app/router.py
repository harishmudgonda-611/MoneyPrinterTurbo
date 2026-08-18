"""Application configuration - root APIRouter.

Defines all FastAPI application endpoints.
"""

from fastapi import APIRouter

from app.controllers.v1 import creative, llm, product, reference, reference_reel, reel, video

root_api_router = APIRouter()
# v1
root_api_router.include_router(video.router)
root_api_router.include_router(llm.router)
root_api_router.include_router(product.router)
root_api_router.include_router(creative.router)
root_api_router.include_router(reel.router)
root_api_router.include_router(reference.router)
root_api_router.include_router(reference_reel.router)
