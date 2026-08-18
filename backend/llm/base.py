from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Single interface every LLM provider implements. Swap providers without touching
    business logic by changing LLM_PROVIDER (groq / gemini / ollama / mock)."""

    name: str = "base"

    @property
    def is_available(self) -> bool:
        return True

    @abstractmethod
    def generate(self, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        """Send a prompt and return the raw model text response."""