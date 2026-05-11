"""Provider-agnostic LLM client backed by LiteLLM.

This isolates the rest of DuckTap from any single vendor SDK. Used (optionally)
by:
- the `polish` step to rewrite operation descriptions
- the `crowd-sniff` step to summarize existing community CLIs
- the `vision` step to interpret screenshots of docs pages
- the auth-doctor to suggest env var names
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


DEFAULT_MODEL = os.environ.get("DUCKTAP_MODEL", "anthropic/claude-3-5-sonnet-latest")


class LLM:
    """Thin wrapper around LiteLLM. Lazy import so DuckTap works without it
    if the user never invokes an LLM step."""

    def __init__(self, model: str | None = None, **opts: Any):
        self.model = model or DEFAULT_MODEL
        self.opts = opts

    def complete(self, messages: list[Message], **kwargs: Any) -> str:
        try:
            import litellm
        except ImportError as e:
            raise RuntimeError(
                "LLM features require litellm. Install with: pip install litellm"
            ) from e
        resp = litellm.completion(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **{**self.opts, **kwargs},
        )
        return resp.choices[0].message.content or ""


def chat(prompt: str, *, system: str | None = None, model: str | None = None,
         **kwargs: Any) -> str:
    """One-shot chat helper."""
    msgs: list[Message] = []
    if system:
        msgs.append(Message("system", system))
    msgs.append(Message("user", prompt))
    return LLM(model=model).complete(msgs, **kwargs)


SUPPORTED_PROVIDERS = {
    "anthropic": "anthropic/<model>  (set ANTHROPIC_API_KEY)",
    "openai": "openai/<model>  (set OPENAI_API_KEY)",
    "gemini": "gemini/<model>  (set GEMINI_API_KEY)",
    "ollama": "ollama/<model>  (local, set OLLAMA_API_BASE)",
    "groq": "groq/<model>  (set GROQ_API_KEY)",
    "azure": "azure/<deployment>  (set AZURE_API_KEY, AZURE_API_BASE)",
}
