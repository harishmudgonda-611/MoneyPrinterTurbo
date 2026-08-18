import json
from unittest.mock import patch

import pytest

from app.models.creative import CreativeGenerateRequest
from app.models.product import ProductData
from app.services.creative_orchestrator import generate_creative


@pytest.fixture
def product():
    return ProductData(
        url="https://example.com/product",
        title="Everyday Cotton Kurti",
        description="Lightweight cotton kurti for daily wear.",
        brand="Example Brand",
        price="799",
        currency="INR",
        availability="InStock",
        category="Kurti",
    )


def test_generate_creative_normalizes_scene_timeline(product):
    request = CreativeGenerateRequest(
        product_url="https://example.com/product",
        language="English",
        duration_seconds=20,
    )
    payload = {
        "hook": "This kurti makes everyday dressing easy.",
        "concept": "Fast product-first styling Reel.",
        "target_audience": "Women looking for comfortable daily wear.",
        "tone": "energetic",
        "duration_seconds": 20,
        "voiceover_script": "Meet an easy everyday cotton kurti.",
        "scenes": [
            {"scene_number": 1, "duration_seconds": 2, "visual_direction": "Product hero", "on_screen_text": "Everyday comfort", "voiceover": "Meet your everyday kurti."},
            {"scene_number": 2, "duration_seconds": 3, "visual_direction": "Show fabric close-up", "on_screen_text": "Lightweight cotton", "voiceover": "Lightweight cotton keeps it easy."},
        ],
        "cta": "Check it out.",
        "caption": "Simple everyday style.",
        "hashtags": ["#kurti", "#fashion"],
    }

    with patch(
        "app.services.creative_orchestrator.llm._generate_response",
        return_value=json.dumps(payload),
    ):
        creative = generate_creative(product, request)

    assert creative.duration_seconds == 20
    assert len(creative.scenes) == 2
    assert sum(scene.duration_seconds for scene in creative.scenes) == pytest.approx(20.0)


def test_generate_creative_rejects_invalid_json(product):
    request = CreativeGenerateRequest(product_url="https://example.com/product")

    with patch(
        "app.services.creative_orchestrator.llm._generate_response",
        return_value="not json",
    ):
        with pytest.raises(ValueError, match="invalid creative JSON"):
            generate_creative(product, request)
