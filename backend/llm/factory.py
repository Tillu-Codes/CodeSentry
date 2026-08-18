import json
import os
import re

from llm.base import LLMClient
from llm.providers import OpenAICompatibleClient


class NullClient(LLMClient):
    """Used when no provider is configured so /scan keeps working without an LLM."""

    name = "none"

    @property
    def is_available(self) -> bool:
        return False

    def generate(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        return ""


class MockClient(LLMClient):
    """Deterministic offline provider: echoes a canned explanation for every finding."""

    name = "mock"

    def generate(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        match = re.search(r"FINDINGS:\n(\[.*\])", prompt, re.S)
        if match:
            try:
                findings = json.loads(match.group(1))
                return json.dumps(
                    [
                        {
                            "index": i,
                            "explanation": f"[mock] Explanation for {f.get('type', 'issue')}.",
                            "suggested_fix": f"# [mock] suggested fix for {f.get('type', 'issue')}",
                        }
                        for i, f in enumerate(findings)
                    ]
                )
            except (json.JSONDecodeError, AttributeError):
                pass
        return "[]"


def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider == "groq":
        return OpenAICompatibleClient(
            name="groq",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY", ""),
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        )
    if provider == "gemini":
        return OpenAICompatibleClient(
            name="gemini",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        )
    if provider == "ollama":
        return OpenAICompatibleClient(
            name="ollama",
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("OLLAMA_API_KEY", ""),
            model=os.getenv("OLLAMA_MODEL", "deepseek-coder"),
        )
    if provider == "mock":
        return MockClient()
    return NullClient()