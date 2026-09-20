"""Shared SentenceTransformer embedding model singleton and encoding utilities."""

import logging
from functools import cache
from typing import Any

import numpy as np
import torch
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

_logger = logging.getLogger(__name__)

_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"

_DEFAULT_QUERY_PROMPT = (
    "Instruct: Given a student's question about a school science or mathematics "
    "topic, retrieve the textbook passage that answers it\nQuery:"
)


@cache
def get_embedding_model() -> SentenceTransformer:
    """Load cached SentenceTransformer embedding model on GPU or CPU with fallback."""
    if torch.cuda.is_available():
        try:
            return SentenceTransformer(_MODEL_NAME, device="cuda")
        except Exception as exc:
            _logger.warning(
                "Failed to init embedding model on CUDA: %s. Falling back to CPU.",
                exc,
            )
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    return SentenceTransformer(_MODEL_NAME, device="cpu")


def get_tokenizer() -> Any:
    """Return the embedding model's tokenizer for token-aligned chunk sizing."""
    return get_embedding_model().tokenizer


def embed_texts(
    texts: list[str],
    query: bool = False,
    prompt: str | None = None,
) -> NDArray[np.float32]:
    """Embed a list of text strings into normalized float32 vectors."""
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    query_prompt = prompt or _DEFAULT_QUERY_PROMPT if query else None

    return get_embedding_model().encode(
        texts,
        prompt=query_prompt,
        normalize_embeddings=True,
        batch_size=8,
    )
