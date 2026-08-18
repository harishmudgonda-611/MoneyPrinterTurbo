from app.services import product_intelligence


class FakeResponse:
    encoding = "utf-8"
    url = "https://example.com/product/red-kurti"
    headers = {"content-type": "text/html; charset=utf-8"}

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=65536):
        yield self.html.encode("utf-8")

    html = '''
    <html>
      <head>
        <title>Fallback title</title>
        <meta property="og:title" content="Red Cotton Kurti">
        <meta property="og:description" content="Comfortable cotton kurti">
        <meta property="product:price:amount" content="799">
        <meta property="product:price:currency" content="INR">
        <meta property="og:image" content="/images/kurti.jpg">
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Product",
          "name": "Red Cotton Kurti",
          "brand": {"@type": "Brand", "name": "Demo Brand"},
          "description": "Comfortable cotton kurti",
          "category": "Kurti",
          "image": ["https://example.com/images/kurti-main.jpg"],
          "offers": {"price": "799", "priceCurrency": "INR", "availability": "https://schema.org/InStock"}
        }
        </script>
      </head>
      <body><img src="/images/secondary.jpg"></body>
    </html>
    '''


def test_analyze_product_extracts_standard_metadata(monkeypatch):
    monkeypatch.setattr(product_intelligence, "_validate_public_url", lambda url: url)
    monkeypatch.setattr(product_intelligence.requests, "get", lambda *args, **kwargs: FakeResponse())

    product = product_intelligence.analyze_product_url("https://example.com/product/red-kurti")

    assert product.title == "Red Cotton Kurti"
    assert product.brand == "Demo Brand"
    assert product.price == "799"
    assert product.currency == "INR"
    assert product.availability == "InStock"
    assert product.category == "Kurti"
    assert product.images[0].url == "https://example.com/images/kurti-main.jpg"
    assert product.canonical_url == "https://example.com/product/red-kurti"
