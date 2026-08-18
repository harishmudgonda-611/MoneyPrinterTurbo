import json
import re
from typing import Any

from app.models.creative import CreativeGenerateRequest, CreativePlan
from app.models.product import ProductData
from app.services import llm

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def _product_context(product: ProductData) -> dict[str, Any]:
    return {
        "title": product.title,
        "description": product.description,
        "brand": product.brand,
        "price": product.price,
        "currency": product.currency,
        "availability": product.availability,
        "category": product.category,
        "images": [image.url for image in product.images[:8]],
        "url": product.canonical_url or product.url,
    }


def _extract_json(text: str) -> dict[str, Any]:
    candidate = text.strip()
    match = _JSON_BLOCK_RE.search(candidate)
    if match:
        candidate = match.group(1).strip()

    # Some compatible providers prepend a short sentence before the JSON object.
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        candidate = candidate[start : end + 1]

    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM returned invalid creative JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("LLM returned a creative payload that is not an object")
    return value


def _validate_creative(payload: dict[str, Any], request: CreativeGenerateRequest) -> CreativePlan:
    creative = CreativePlan.model_validate(payload)
    if creative.duration_seconds != request.duration_seconds:
        creative = creative.model_copy(update={"duration_seconds": request.duration_seconds})

    # Keep the scene timeline bounded and deterministic for the renderer.
    total = sum(scene.duration_seconds for scene in creative.scenes)
    if total <= 0:
        raise ValueError("Creative scene timeline is empty")
    scale = request.duration_seconds / total
    scenes = [
        scene.model_copy(update={"duration_seconds": round(scene.duration_seconds * scale, 2)})
        for scene in creative.scenes
    ]
    return creative.model_copy(update={"scenes": scenes})


def generate_creative(product: ProductData, request: CreativeGenerateRequest) -> CreativePlan:
    context = json.dumps(_product_context(product), ensure_ascii=False)
    price_rule = "Show the verified product price when available." if request.include_price else "Do not mention price."
    cta_rule = "End with a clear, non-spammy purchase/action CTA." if request.include_cta else "Do not include a CTA."

    prompt = f"""
You are a senior short-form performance creative director.
Create an ORIGINAL vertical product Reel plan. Do not copy any existing advertisement.
Use only product facts supplied below. Never invent discounts, specifications, reviews,
ratings, guarantees, stock levels, or claims that are not present in the data.

OUTPUT: Return ONLY valid JSON. No markdown and no commentary.

Required JSON shape:
{{
  "hook": "...",
  "concept": "...",
  "target_audience": "...",
  "tone": "...",
  "duration_seconds": {request.duration_seconds},
  "voiceover_script": "...",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_seconds": 3,
      "visual_direction": "...",
      "on_screen_text": "...",
      "voiceover": "..."
    }}
  ],
  "cta": "...",
  "caption": "...",
  "hashtags": ["..."]
}}

Constraints:
- Language: {request.language}
- Platform: {request.platform}
- Requested duration: {request.duration_seconds} seconds
- Tone: {request.tone}
- Use 4-8 scenes for a short Reel.
- Hook must work in the first 1-2 seconds.
- Visual directions must be actionable for a video renderer using product images/video.
- On-screen text must be short and mobile readable.
- Voiceover must sound natural when spoken aloud.
- {price_rule}
- {cta_rule}
- Keep the creative conversion-focused without making unsupported claims.

PRODUCT DATA:
{context}
""".strip()

    response = llm._generate_response(prompt)
    if not response or response.startswith("Error:"):
        detail = response.removeprefix("Error:").strip() if response else "empty LLM response"
        raise RuntimeError(f"Creative generation failed: {detail}")

    payload = _extract_json(response)
    return _validate_creative(payload, request)
