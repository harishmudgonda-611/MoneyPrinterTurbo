# Product Reel Engine

This fork adds a product-first Reel workflow on top of the existing MoneyPrinterTurbo renderer.

## End-to-end API

`POST /api/v1/reels/product/generate`

Flow:

1. Analyze a public product URL.
2. Extract verified product facts and product images.
3. Generate an original short-form creative plan.
4. Download and normalize product images into MoneyPrinterTurbo local materials.
5. Use product images as the default visual source; fall back to Pexels when the page has no usable images.
6. Queue the existing MoneyPrinterTurbo worker.
7. Render a 9:16 MP4 with TTS, subtitles and optional background music.
8. Query the normal `/api/v1/tasks/{task_id}` endpoint for progress and final video URLs.

The existing MoneyPrinterTurbo video pipeline remains the rendering engine; this layer is orchestration and product intelligence.
