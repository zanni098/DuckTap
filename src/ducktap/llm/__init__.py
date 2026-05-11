"""LLM provider abstraction (Anthropic / OpenAI / Gemini / Ollama via LiteLLM)."""
from ducktap.llm.base import LLM, Message, chat
__all__ = ["LLM", "Message", "chat"]
