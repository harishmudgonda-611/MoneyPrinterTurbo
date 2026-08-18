from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.models.product import ProductData


class CreativeGenerateRequest(BaseModel):
    product_url: HttpUrl
    language: str = Field(default="English", min_length=2, max_length=32)
    duration_seconds: int = Field(default=20, ge=8, le=60)
    tone: str = Field(default="high-energy, trustworthy, social-first", min_length=3, max_length=100)
    platform: Literal["instagram", "youtube_shorts", "tiktok"] = "instagram"
    include_price: bool = True
    include_cta: bool = True


class CreativeScene(BaseModel):
    scene_number: int = Field(ge=1)
    duration_seconds: float = Field(gt=0)
    visual_direction: str = Field(min_length=1, max_length=500)
    on_screen_text: str = Field(default="", max_length=180)
    voiceover: str = Field(default="", max_length=1000)


class CreativePlan(BaseModel):
    hook: str = Field(min_length=1, max_length=240)
    concept: str = Field(min_length=1, max_length=500)
    target_audience: str = Field(min_length=1, max_length=240)
    tone: str = Field(min_length=1, max_length=120)
    duration_seconds: int = Field(ge=8, le=60)
    voiceover_script: str = Field(min_length=1, max_length=6000)
    scenes: list[CreativeScene] = Field(min_length=1, max_length=12)
    cta: str = Field(default="", max_length=240)
    caption: str = Field(default="", max_length=1000)
    hashtags: list[str] = Field(default_factory=list, max_length=20)


class CreativeGenerateResponse(BaseModel):
    product: ProductData
    creative: CreativePlan
