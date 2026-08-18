from unittest.mock import Mock, patch

from app.models.creative import CreativePlan, CreativeScene
from app.models.product import ProductData
from app.models.product_reel import ProductReelGenerateRequest
from app.services.product_reel_renderer import _build_search_terms, queue_product_reel


def test_build_search_terms_preserves_scene_order():
    product = ProductData(
        url="https://example.com/product",
        title="Cotton Kurti",
        category="Kurti",
    )
    creative = CreativePlan(
        hook="Hook",
        concept="Product-first fashion Reel",
        target_audience="Women",
        tone="energetic",
        duration_seconds=20,
        voiceover_script="Try this kurti.",
        scenes=[
            CreativeScene(scene_number=1, duration_seconds=5, visual_direction="kurti hero shot"),
            CreativeScene(scene_number=2, duration_seconds=5, visual_direction="fabric close up"),
        ],
    )

    assert _build_search_terms(product, creative) == [
        "kurti hero shot",
        "fabric close up",
        "Kurti Cotton Kurti",
    ]


def test_queue_product_reel_builds_portrait_renderer_task():
    product = ProductData(
        url="https://example.com/product",
        title="Cotton Kurti",
        category="Kurti",
    )
    creative = CreativePlan(
        hook="Hook",
        concept="Product-first fashion Reel",
        target_audience="Women",
        tone="energetic",
        duration_seconds=20,
        voiceover_script="Try this kurti.",
        scenes=[
            CreativeScene(scene_number=1, duration_seconds=10, visual_direction="kurti hero shot"),
            CreativeScene(scene_number=2, duration_seconds=10, visual_direction="fabric close up"),
        ],
        cta="Check it out.",
    )
    body = ProductReelGenerateRequest(product_url="https://example.com/product")

    with patch(
        "app.services.product_reel_renderer.analyze_product_url",
        return_value=product,
    ), patch(
        "app.services.product_reel_renderer.generate_creative",
        return_value=creative,
    ), patch(
        "app.services.product_reel_renderer.task_manager.add_task",
    ) as add_task, patch(
        "app.services.product_reel_renderer.sm.state.update_task",
    ), patch(
        "app.services.product_reel_renderer.utils.get_uuid",
        return_value="test-task-id",
    ):
        task_id, result_product, result_creative = queue_product_reel(body)

    assert task_id == "test-task-id"
    assert result_product is product
    assert result_creative is creative
    params = add_task.call_args.kwargs["params"]
    assert params.video_aspect.value == "9:16"
    assert params.video_count == 1
    assert params.match_materials_to_script is True
    assert params.video_script.endswith("Check it out.")
