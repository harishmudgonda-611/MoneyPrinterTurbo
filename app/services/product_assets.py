"""Download and normalize product images for the local MoneyPrinterTurbo renderer."""

import io
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from PIL import Image

from app.models.schema import MaterialInfo
from app.utils import utils

MAX_IMAGE_BYTES = 8 * 1024 * 1024
TIMEOUT = (10, 30)
_ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".jpg"}


def _assert_public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Product image URL must be public http(s)")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"}:
        raise ValueError("Local product image URLs are not allowed")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Unable to resolve product image host") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ValueError("Private or local product image URLs are not allowed")


def _download_image(url: str, output_path: Path) -> Path | None:
    _assert_public_host(url)
    response = requests.get(
        url,
        headers={"User-Agent": "MoneyPrinterTurbo Product Asset Engine/1.0"},
        timeout=TIMEOUT,
        allow_redirects=True,
        stream=True,
    )
    response.raise_for_status()
    _assert_public_host(response.url)

    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in _ALLOWED_TYPES:
        return None

    content = bytearray()
    for chunk in response.iter_content(64 * 1024):
        if not chunk:
            continue
        content.extend(chunk)
        if len(content) > MAX_IMAGE_BYTES:
            return None

    suffix = _ALLOWED_TYPES[content_type]
    target = output_path.with_suffix(suffix)

    try:
        with Image.open(io.BytesIO(bytes(content))) as image:
            image.load()
            if suffix == ".png":
                normalized = image.convert("RGBA")
                buffer = io.BytesIO()
                normalized.save(buffer, format="PNG")
            else:
                normalized = image.convert("RGB")
                buffer = io.BytesIO()
                normalized.save(buffer, format="JPEG", quality=95)
        target.write_bytes(buffer.getvalue())
    except Exception:
        target.unlink(missing_ok=True)
        return None

    return target


def prepare_product_assets(image_urls: list[str], max_images: int = 8) -> list[MaterialInfo]:
    """Download verified product images into MPT's local material directory."""
    target_dir = Path(utils.storage_dir("local_videos", create=True))
    materials: list[MaterialInfo] = []
    seen: set[str] = set()

    for image_url in image_urls[:max_images]:
        if not isinstance(image_url, str) or not image_url.strip() or image_url in seen:
            continue
        seen.add(image_url)
        stem = target_dir / f"product-{uuid4().hex}"
        try:
            saved = _download_image(image_url, stem)
            if saved is None:
                continue
            materials.append(
                MaterialInfo(
                    provider="product",
                    url=saved.name,
                    duration=4,
                    source_info={"provider": "product", "source_page": image_url},
                )
            )
        except Exception:
            # One bad retailer CDN image must not kill the complete Reel. The renderer
            # will use the successfully downloaded subset and can fall back to stock.
            continue

    return materials
