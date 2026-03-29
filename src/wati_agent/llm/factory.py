from wati_agent.app.config import Settings
from wati_agent.llm.base import BaseLLMProvider
from wati_agent.llm.ollama_provider import OllamaProvider
from wati_agent.llm.openai_provider import OpenAIProvider


def build_llm_provider(settings: Settings) -> BaseLLMProvider:
    provider = settings.llm_provider.lower()

    if provider == "openai":
        return OpenAIProvider(model=settings.openai_model, api_key=settings.openai_api_key)

    return OllamaProvider(
        model=settings.ollama_model,
        host=settings.ollama_host,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
