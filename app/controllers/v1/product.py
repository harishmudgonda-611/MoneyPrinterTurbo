from fastapi import HTTPException
from loguru import logger

from app.controllers.v1.base import new_router
from app.models.product import ProductAnalyzeRequest, ProductAnalyzeResponse
from app.services.product_intelligence import analyze_product_url

router = new_router()


@router.post(
    "/products/analyze",
    response_model=ProductAnalyzeResponse,
    summary="Analyze a product page",
)
def analyze_product(body: ProductAnalyzeRequest):
    try:
        product = analyze_product_url(str(body.url), include_html=body.include_html)
        return {"product": product}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("product analysis failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to analyze the product page",
        ) from exc
