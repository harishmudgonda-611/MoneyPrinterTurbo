from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.models.product import ProductData
from app.models.creative import CreativePlan


class ProductReelGenerateRequest(BaseModel):
    product_url: HttpUrl
    language: str = Field(default="English", min_length=2, max_length=32)
    duration_seconds: int = Field(default=20, ge=8, le=60)
    tone: str = Field(default="high-energy, trustworthy, social-first", min_length=3, max_length=100)
    platform: Literal["instagram", "youtube_shorts", "tiktok"] = "instagram"
    video_source: Literal["pexels", "pixabay", "coverr"] = "pexels"
    voice_name: str = Field(default="", max_length=120)
    voice_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    bgm_volume: float = Field(default=0.2, ge=0.0, le=1.0)
    include_price: bool = True
    include_cta: bool = True


class ProductReelGenerateResponse(BaseModel):
    task_id: str
    status: str = "queued"
    product: ProductData
    creative: CreativePlan
    renderer: str = "moneyprinterturbo"
    aspect_ratio: str = "9:16"
