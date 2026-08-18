from fastapi import HTTPException
from loguru import logger

from app.controllers.v1.base import new_router
from app.models.reference_reel import ReferenceGuidedGenerateRequest, ReferenceGuidedGenerateResponse
from app.services.reference_reel_renderer import queue_reference_guided_reel

router = new_router()


@router.post(
    "/reels/reference-guided/generate",
    response_model=ReferenceGuidedGenerateResponse,
    summary="Generate an original product Reel from a reference analysis",
)
def generate_reference_guided_reel(body: ReferenceGuidedGenerateRequest):
    try:
        task_id, product, creative, reference = queue_reference_guided_reel(body)
        return {
            "task_id": task_id,
            "status": "queued",
            "product": product,
            "creative": creative,
            "reference_id": reference.reference_id,
            "renderer": "moneyprinterturbo",
            "aspect_ratio": "9:16",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.warning("reference-guided Reel generation failed: {}", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("reference-guided Reel generation failed")
        raise HTTPException(status_code=502, detail="Unable to queue the reference-guided Reel") from exc
