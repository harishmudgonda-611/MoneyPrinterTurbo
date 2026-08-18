"""Bridge the product creative and product assets into MoneyPrinterTurbo."""

from app.controllers.v1.video import task_manager
from app.models.creative import CreativeGenerateRequest
from app.models.product import ProductData
from app.models.product_reel import ProductReelGenerateRequest
from app.models.schema import TaskVideoRequest, VideoAspect, VideoConcatMode
from app.services import state as sm
from app.services.creative_orchestrator import generate_creative
from app.services.product_assets import prepare_product_assets
from app.services.product_intelligence import analyze_product_url
from app.services.reel_task_runner import start_reel_task
from app.utils import utils


def _build_search_terms(product: ProductData, creative) -> list[str]:
    """Turn scene directions into ordered fallback stock-footage search terms."""
    terms: list[str] = []
    for scene in creative.scenes:
        direction = scene.visual_direction.strip()
        if direction and direction not in terms:
            terms.append(direction[:180])

    fallback = " ".join(
        part for part in [product.brand, product.category, product.title] if part
    ).strip()
    if fallback and len(terms) < 4:
        terms.append(fallback[:180])
    return terms[:8]


def queue_product_reel(body: ProductReelGenerateRequest) -> tuple[str, ProductData, object]:
    """Analyze, create the creative, prepare assets, and enqueue the existing MPT worker."""
    product = analyze_product_url(str(body.product_url), include_html=False)
    creative_request = CreativeGenerateRequest(
        product_url=body.product_url,
        language=body.language,
        duration_seconds=body.duration_seconds,
        tone=body.tone,
        platform=body.platform,
        include_price=body.include_price,
        include_cta=body.include_cta,
    )
    creative = generate_creative(product, creative_request)

    script = creative.voiceover_script.strip()
    if creative.cta and body.include_cta and creative.cta not in script:
        script = f"{script} {creative.cta}".strip()

    product_materials = []
    selected_source = body.video_source
    if body.video_source == "product_first":
        product_materials = prepare_product_assets([image.url for image in product.images])
        if product_materials:
            selected_source = "local"
        else:
            selected_source = "pexels"

    params = TaskVideoRequest(
        video_subject=(product.title or creative.concept)[:500],
        video_script=script,
        video_terms=_build_search_terms(product, creative),
        video_aspect=VideoAspect.portrait,
        video_concat_mode=VideoConcatMode.sequential,
        video_clip_duration=4,
        match_materials_to_script=True,
        video_count=1,
        video_source=selected_source,
        video_materials=product_materials or None,
        video_language=body.language,
        voice_name=body.voice_name,
        voice_rate=body.voice_rate,
        bgm_volume=body.bgm_volume,
        subtitle_enabled=True,
        paragraph_number=1,
    )

    task_id = utils.get_uuid()
    sm.state.update_task(
        task_id,
        product_url=str(body.product_url),
        reel_mode=True,
        renderer="moneyprinterturbo",
        aspect_ratio="9:16",
        asset_mode="product_first" if product_materials else "stock_fallback",
        product_asset_count=len(product_materials),
        renderer_source=selected_source,
        product_title=product.title,
        creative_hook=creative.hook,
        creative_concept=creative.concept,
    )
    task_manager.add_task(start_reel_task, task_id=task_id, params=params, stop_at="video")
    return task_id, product, creative
