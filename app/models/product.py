from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


class ProductAnalyzeRequest(BaseModel):
    url: HttpUrl
    include_html: bool = False


class ProductImage(BaseModel):
    url: str
    source: str = "page"


class ProductData(BaseModel):
    url: str
    title: str = ""
    description: str = ""
    brand: str = ""
    price: Optional[str] = None
    currency: Optional[str] = None
    availability: Optional[str] = None
    category: str = ""
    images: list[ProductImage] = Field(default_factory=list)
    canonical_url: Optional[str] = None
    source: str = "webpage"
    raw: dict[str, Any] = Field(default_factory=dict)


class ProductAnalyzeResponse(BaseModel):
    product: ProductData
