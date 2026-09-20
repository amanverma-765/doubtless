"""Centralized LLM client initialization and model access."""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from doubtless.config import AI_API_KEY, AI_BASE_URL, AI_MODEL_NAME

ai_model = OpenAIChatModel(
    model_name=AI_MODEL_NAME,
    provider=OpenAIProvider(base_url=AI_BASE_URL, api_key=AI_API_KEY),
)


def get_ai_model() -> OpenAIChatModel:
    """Return the configured OpenAIChatModel instance."""
    return ai_model
