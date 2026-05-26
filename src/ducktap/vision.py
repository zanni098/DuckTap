"""Vision: LLM-powered screenshot reading for sniffing.

Captures a screenshot of a webpage and sends it to a vision-capable LLM
(via LiteLLM) to extract API documentation structure.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None  # type: ignore[assignment]

from ducktap.llm.base import LLM, Message


@dataclass
class VisionResult:
    raw_text: str
    extracted_endpoints: list[dict[str, Any]]


def screenshot_to_text(url: str, model: str | None = None) -> str:
    """Capture a screenshot of *url* and describe it with a vision LLM."""
    if sync_playwright is None:
        raise RuntimeError("Playwright is required for vision. Install with: pip install playwright")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(url, wait_until="networkidle", timeout=30000)
        png_bytes = page.screenshot(full_page=False)
        browser.close()

    b64 = base64.b64encode(png_bytes).decode("ascii")

    llm = LLM(model=model or "anthropic/claude-3-5-sonnet-latest")
    prompt = (
        "Describe the API documentation visible in this screenshot. "
        "List any endpoint paths, HTTP methods, and parameter names you can see."
    )
    # LiteLLM vision format
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ]
    # type: ignore[arg-type]  # LiteLLM accepts mixed content
    messages = [Message("user", str(content))]
    return llm.complete(messages)
