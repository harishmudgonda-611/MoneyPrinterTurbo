from fastapi import HTTPException
from loguru import logger

from app.controllers.v1.base import new_router
from app.models.product_reel import ProductReelGenerateRequest, ProductReelGenerateResponse
from app.services.product_reel_renderer import queue_product_reel

router = new_router()


@router.post(
    "/reels/product/generate",
    response_model=ProductReelGenerateResponse,
    summary="Generate a product Reel",
)
def generate_product_reel(body: ProductReelGenerateRequest):
    try:
        task_id, product, creative = queue_product_reel(body)
        return {
            "task_id": task_id,
            "status": "queued",
            "product": product,
            "creative": creative,
            "renderer": "moneyprinterturbo",
            "aspect_ratio": "9:16",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.warning("product Reel generation failed: {}", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("product Reel generation failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to queue the product Reel",
        ) from exc
