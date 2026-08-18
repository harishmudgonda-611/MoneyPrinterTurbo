"""Queue a reference-guided product Reel through the existing renderer."""

from pathlib import Path

from app.controllers.v1.video import task_manager
from app.models.reference_reel import ReferenceGuidedGenerateRequest
from app.models.creative import CreativeGenerateRequest
from app.models.schema import TaskVideoRequest, VideoAspect, VideoConcatMode
from app.services import state as sm
from app.services import task as tm
from app.services.product_assets import prepare_product_assets
from app.services.product_intelligence import analyze_product_url
from app.services.reference_creative_bridge import generate_reference_guided_creative
from app.services.reference_video import _run_ffprobe
from app.utils import utils


def _reference_path(reference_id: str) -> str:
    directory = Path(utils.storage_dir("reference_videos", create=True)).resolve()
    matches = list(directory.glob(f"{reference_id}.*"))
    if len(matches) != 1:
        raise ValueError("Reference video was not found")
    path = matches[0].resolve()
    if path.parent != directory:
        raise ValueError("Invalid reference video path")
    return str(path)


def _build_search_terms(product, creative) -> list[str]:
    terms = []
    for scene in creative.scenes:
        direction = scene.visual_direction.strip()
        if direction and direction not in terms:
            terms.append(direction[:180])
    fallback = " ".join(
        p for p in [product.brand, product.category, product.title] if p
    ).strip()
    if fallback and len(terms) < 4:
        terms.append(fallback[:180])
    return terms[:8]


def queue_reference_guided_reel(body: ReferenceGuidedGenerateRequest):
    reference_path = _reference_path(body.reference_id)
    _run_ffprobe(reference_path)

    from app.services.reference_video import analyze_reference_video

    reference = analyze_reference_video(reference_path, body.reference_id)
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
    creative = generate_reference_guided_creative(product, creative_request, reference)

    script = creative.voiceover_script.strip()
    if creative.cta and body.include_cta and creative.cta not in script:
        script = f"{script} {creative.cta}".strip()

    # Reference analysis controls the creative; the actual product assets control
    # the visuals. This prevents the renderer from silently substituting generic
    # stock footage when the product page contains usable images.
    product_materials = prepare_product_assets(
        [image.url for image in product.images]
    )
    if not product_materials:
        raise ValueError("No usable product images were found on the product page")

    params = TaskVideoRequest(
        video_subject=(product.title or creative.concept)[:500],
        video_script=script,
        video_terms=_build_search_terms(product, creative),
        video_aspect=VideoAspect.portrait,
        video_concat_mode=VideoConcatMode.sequential,
        video_clip_duration=4,
        match_materials_to_script=True,
        video_count=1,
        video_source="local",
        video_materials=product_materials,
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
        reference_id=body.reference_id,
        reel_mode=True,
        reference_guided=True,
        renderer="moneyprinterturbo",
        aspect_ratio="9:16",
        asset_mode="product_first",
        product_asset_count=len(product_materials),
        renderer_source="local",
        product_title=product.title,
        creative_hook=creative.hook,
        reference_pacing=reference.pacing,
        reference_shot_count=reference.shot_count,
    )
    task_manager.add_task(tm.start, task_id=task_id, params=params, stop_at="video")
    return task_id, product, creative, reference
