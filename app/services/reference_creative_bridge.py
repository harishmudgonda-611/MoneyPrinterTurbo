"""Apply reference-video principles to an original product Reel creative."""

from app.models.creative import CreativeGenerateRequest, CreativePlan
from app.models.product import ProductData
from app.models.reference_video import ReferenceVideoAnalysis
from app.services import llm
from app.services.creative_orchestrator import _extract_json, _validate_creative, _product_context
import json


def generate_reference_guided_creative(
    product: ProductData,
    request: CreativeGenerateRequest,
    reference: ReferenceVideoAnalysis,
) -> CreativePlan:
    context = json.dumps(_product_context(product), ensure_ascii=False)
    reference_context = json.dumps(
        {
            "duration_seconds": reference.duration_seconds,
            "pacing": reference.pacing,
            "average_shot_seconds": reference.average_shot_seconds,
            "hook_window_seconds": reference.hook_window_seconds,
            "structure": reference.structure,
            "creative_principles": reference.creative_principles,
            "originality_rules": reference.originality_rules,
        },
        ensure_ascii=False,
    )

    prompt = f"""
You are a senior short-form performance creative director.
Create a completely ORIGINAL vertical product Reel using the reference analysis only as
high-level creative guidance. Do not reproduce the reference video's script, wording,
shots, creator, characters, exact sequence, transitions, or distinctive execution.
Every scene must be rebuilt around the supplied product facts and actual product assets.
Never invent product claims, reviews, ratings, discounts, specifications, or guarantees.

Return ONLY valid JSON matching this schema:
{{
  "hook": "...", "concept": "...", "target_audience": "...", "tone": "...",
  "duration_seconds": {request.duration_seconds}, "voiceover_script": "...",
  "scenes": [{{"scene_number":1,"duration_seconds":3,"visual_direction":"...",
  "on_screen_text":"...","voiceover":"..."}}],
  "cta":"...", "caption":"...", "hashtags":["..."]
}}

Constraints:
- Language: {request.language}
- Platform: {request.platform}
- Duration: {request.duration_seconds}s
- Tone: {request.tone}
- Use 4-8 scenes.
- Make the first 1-2 seconds decisive.
- Target the reference pacing without copying its exact timing or shot sequence.
- Use the reference's useful storytelling principles, but create a distinct concept.
- Keep visual directions practical for product images/video.
- Keep on-screen text short and mobile readable.
- {"Mention the verified price when available." if request.include_price else "Do not mention price."}
- {"End with a clear CTA." if request.include_cta else "Do not include a CTA."}

PRODUCT DATA:
{context}

REFERENCE ANALYSIS:
{reference_context}
""".strip()

    response = llm._generate_response(prompt)
    if not response or response.startswith("Error:"):
        detail = response.removeprefix("Error:").strip() if response else "empty LLM response"
        raise RuntimeError(f"Reference-guided creative generation failed: {detail}")

    return _validate_creative(_extract_json(response), request)
