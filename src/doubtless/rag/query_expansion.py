"""Query expansion for bilingual STEM lecture and NCERT textbook retrieval."""

import logging

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from doubtless.rag.llm import ai_model

logger = logging.getLogger(__name__)

_EXPANSION_SYSTEM_PROMPT = (
    "You are a search query optimizer for STEM video lectures and NCERT books.\n"
    "Given a student search query, generate 2-3 concise search variations:\n"
    "1. Standard formal English scientific/mathematical terms\n"
    "2. Hindi/Devanagari academic equivalent terminology if applicable\n"
    "3. Common conceptual synonyms or standard notation\n\n"
    "Keep each variation brief (1-5 words). Never output explanations."
)


class ExpandedQueriesPayload(BaseModel):
    """Structured search query variations for vector retrieval."""

    queries: list[str] = Field(
        default_factory=list,
        description="2 to 4 diverse search variations (English, Hindi, synonyms)",
    )


_expander_agent = Agent[None, ExpandedQueriesPayload](
    model=ai_model,
    name="query_expander",
    output_type=ExpandedQueriesPayload,
    system_prompt=_EXPANSION_SYSTEM_PROMPT,
    model_settings=ModelSettings(temperature=0.0, timeout=15.0),
)


# ponytail: bounded cache with FIFO eviction (async functions can't use lru_cache)
_MAX_CACHE_ENTRIES = 512
_expansion_cache: dict[str, list[str]] = {}


async def expand_query(query: str) -> list[str]:
    """Expand a search query into technical English and Hindi synonyms.

    Cached in-memory so identical queries avoid redundant LLM invocations.
    Always includes the original query as the primary entry.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    if clean_query in _expansion_cache:
        return _expansion_cache[clean_query]

    variations: list[str] = [clean_query]
    seen: set[str] = {clean_query.lower()}

    try:
        result = await _expander_agent.run(clean_query)
        for q in result.output.queries:
            q_clean = q.strip()
            if q_clean and q_clean.lower() not in seen:
                seen.add(q_clean.lower())
                variations.append(q_clean)
    except Exception as exc:
        logger.warning(
            "Query expansion failed for '%s': %s. Using original query.",
            clean_query,
            exc,
        )

    if len(_expansion_cache) >= _MAX_CACHE_ENTRIES:
        _expansion_cache.pop(next(iter(_expansion_cache)))
    _expansion_cache[clean_query] = variations
    return variations
