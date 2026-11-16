# Topic research ingestion for video creation

MoneyPrinterTurbo's primary workflow is topic/keyword → script → footage matching → subtitles → video. Research ingestion should improve source quality without silently turning the video generator into an unrestricted crawler.

## Adapter map
- **Crawl4AI**: optional conversion of permitted public articles and documentation into clean Markdown for script research.
- **Scrapy**: optional domain-scoped collection for sites that explicitly allow automated crawling.
- **MarkItDown**: optional conversion of operator-provided PDF, DOCX, PPTX, XLSX and HTML research files.
- **AutoScraper / Scrapling**: parser development against saved fixtures, not bot-evasion or CAPTCHA bypass.

## Research evidence model
For each source retain URL, title, publisher, publication date if present, retrieval timestamp, extracted excerpt, content hash and extraction method. Keep source evidence separate from generated script text. Generated claims should be traceable to one or more source records; flag conflicting or undated claims for human review.

## Safe defaults
Research is opt-in and read-only. Respect robots.txt, terms, copyright, rate limits and source attribution. No authentication, paywall or anti-bot bypass. Limit domains, concurrency, response size and timeouts. Do not download or reuse copyrighted footage without rights; source collection does not grant media reuse rights.

## Delivery status
This branch adds a dependency-free offline HTML normalizer at `research/normalize.py` with regression tests at `tests/test_research_normalize.py`. It does not fetch URLs or crawl and does not change the video pipeline. Network adapters remain optional follow-up work behind explicit source allowlists and fixture-based tests.