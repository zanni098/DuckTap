"""Crowd-sniff: study existing community CLIs / MCP servers via web search.

Searches DuckDuckGo for "<api> CLI" and "<api> MCP server", then uses an LLM
to summarize the landscape so DuckTap can learn naming conventions, auth
patterns, and popular operations before generating its own CLI.
"""
from __future__ import annotations

from typing import Any

from ducktap.llm.base import chat


def _search(query: str) -> list[dict[str, str]]:
    """DuckDuckGo text search.  Requires `duckduckgo-search`."""
    try:
        from duckduckgo_search import DDGS
    except ImportError as e:
        raise RuntimeError(
            "crowd-sniff requires duckduckgo-search. "
            "Install with: pip install 'ducktap[search]'"
        ) from e
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=10)
        return [
            {"title": r["title"], "href": r["href"], "body": r["body"]}
            for r in results
        ]


def crowd_sniff(api_name: str, *, model: str | None = None) -> dict[str, Any]:
    """Search the web for existing CLIs and MCP servers, return a summary."""
    queries = [
        f"{api_name} CLI tool",
        f"{api_name} MCP server",
        f"{api_name} command line interface",
    ]
    raw: list[dict[str, Any]] = []
    for q in queries:
        try:
            raw.extend(_search(q))
        except RuntimeError:
            # If search is unavailable, still proceed with LLM if possible
            pass

    # De-duplicate by URL
    seen: set[str] = set()
    unique = [r for r in raw if not (r["href"] in seen or seen.add(r["href"]))]

    prompt = (
        f"API: {api_name}\n\n"
        f"Web results ({len(unique)} unique links):\n"
    )
    for i, r in enumerate(unique[:15], 1):
        prompt += f"{i}. {r['title']}\n   {r['href']}\n   {r['body'][:300]}\n"
    prompt += (
        "\nSummarize: What CLI naming conventions, auth patterns, and "
        "popular operations exist for this API?  Suggest a short list of "
        "operation names that any good CLI should expose."
    )

    try:
        summary = chat(prompt, model=model)
    except RuntimeError:
        summary = "LLM unavailable — install litellm and set an API key."

    return {
        "api": api_name,
        "results_found": len(unique),
        "sources": [{"title": r["title"], "url": r["href"]} for r in unique[:10]],
        "summary": summary,
    }
