"""Product-page extraction for the product Reel workflow.

The extractor is intentionally provider-neutral. It reads standard Open Graph,
Twitter Card and JSON-LD Product metadata first, then falls back to visible
HTML metadata. No retailer-specific scraper is required for the first version.
"""

import html
import ipaddress
import json
import re
import socket
from urllib.parse import urljoin, urlparse

import requests
from loguru import logger

from app.models.product import ProductData, ProductImage


USER_AGENT = (
    "Mozilla/5.0 (compatible; MoneyPrinterTurbo Product Intelligence/1.0; +https://github.com/harry0703/MoneyPrinterTurbo)"
)
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
TIMEOUT_SECONDS = 15


def _validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public http(s) URLs are supported")

    host = parsed.hostname.strip().lower()
    if host in {"localhost", "localhost.localdomain"}:
        raise ValueError("Local URLs are not allowed")

    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Unable to resolve product URL host") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ValueError("Private or local network URLs are not allowed")

    return url


def _clean(value: object) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _meta(html_text: str, key: str) -> str:
    patterns = [
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']*)["\']',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{re.escape(key)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, re.I)
        if match:
            return _clean(match.group(1))
    return ""


def _json_ld_objects(html_text: str) -> list[dict]:
    objects: list[dict] = []
    for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_text, re.I | re.S):
        try:
            data = json.loads(html.unescape(raw.strip()))
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if isinstance(item, dict):
                if "@graph" in item and isinstance(item["@graph"], list):
                    objects.extend(x for x in item["@graph"] if isinstance(x, dict))
                objects.append(item)
    return objects


def _find_product(objects: list[dict]) -> dict:
    for item in objects:
        types = item.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(str(t).lower() == "product" for t in types):
            return item
    return {}


def _extract_price(product: dict) -> tuple[str | None, str | None, str | None]:
    offers = product.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}
    price = offers.get("price") or product.get("price")
    currency = offers.get("priceCurrency") or product.get("priceCurrency")
    availability = offers.get("availability") or product.get("availability")
    if isinstance(availability, str):
        availability = availability.rsplit("/", 1)[-1]
    return (_clean(price) or None, _clean(currency) or None, _clean(availability) or None)


def _extract_images(html_text: str, product: dict, base_url: str) -> list[ProductImage]:
    candidates: list[tuple[str, str]] = []

    image = product.get("image")
    if isinstance(image, str):
        candidates.append((image, "json-ld"))
    elif isinstance(image, list):
        candidates.extend((str(x), "json-ld") for x in image if isinstance(x, str))

    for key in ("og:image", "twitter:image"):
        value = _meta(html_text, key)
        if value:
            candidates.append((value, "open-graph"))

    for match in re.finditer(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']', html_text, re.I):
        candidates.append((match.group(1), "page"))
        if len(candidates) >= 30:
            break

    result: list[ProductImage] = []
    seen: set[str] = set()
    for image_url, source in candidates:
        absolute = urljoin(base_url, html.unescape(image_url).strip())
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or absolute in seen:
            continue
        seen.add(absolute)
        result.append(ProductImage(url=absolute, source=source))
        if len(result) >= 12:
            break
    return result


def analyze_product_url(url: str, include_html: bool = False) -> ProductData:
    target = _validate_public_url(str(url))
    response = requests.get(
        target,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        timeout=TIMEOUT_SECONDS,
        allow_redirects=True,
        stream=True,
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise ValueError("Product URL did not return an HTML page")

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            break
        chunks.append(chunk)
    html_text = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")

    objects = _json_ld_objects(html_text)
    product = _find_product(objects)

    name = product.get("name") if product else ""
    description = product.get("description") if product else ""
    brand = product.get("brand") if product else ""
    if isinstance(brand, dict):
        brand = brand.get("name", "")

    title = _clean(name) or _meta(html_text, "og:title") or _meta(html_text, "twitter:title")
    if not title:
        match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
        title = _clean(match.group(1)) if match else ""

    description = _clean(description) or _meta(html_text, "og:description") or _meta(html_text, "description")
    brand = _clean(brand)
    price, currency, availability = _extract_price(product)

    if not price:
        price = _meta(html_text, "product:price:amount") or None
    if not currency:
        currency = _meta(html_text, "product:price:currency") or None

    category = _clean(product.get("category", "")) if product else ""
    canonical = _meta(html_text, "og:url")
    canonical = canonical or (re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', html_text, re.I) or [None, ""])[1]
    canonical = urljoin(response.url, canonical) if canonical else response.url

    raw = {}
    if include_html:
        raw["html"] = html_text
    raw["final_url"] = response.url
    raw["json_ld"] = objects[:10]

    logger.info("product analyzed: {}", response.url)
    return ProductData(
        url=target,
        title=title,
        description=description,
        brand=brand,
        price=price,
        currency=currency,
        availability=availability,
        category=category,
        images=_extract_images(html_text, product, response.url),
        canonical_url=canonical,
        raw=raw,
    )
