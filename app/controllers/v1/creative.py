from fastapi import HTTPException
from loguru import logger

from app.controllers.v1.base import new_router
from app.models.creative import CreativeGenerateRequest, CreativeGenerateResponse
from app.services.creative_orchestrator import generate_creative
from app.services.product_intelligence import analyze_product_url

router = new_router()


@router.post(
    "/creatives/generate",
    response_model=CreativeGenerateResponse,
    summary="Generate a product Reel creative plan",
)
def create_creative(body: CreativeGenerateRequest):
    try:
        product = analyze_product_url(str(body.product_url), include_html=False)
        creative = generate_creative(product, body)
        return {"product": product, "creative": creative}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.warning("creative generation failed: {}", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("creative generation failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to generate the product creative",
        ) from exc
