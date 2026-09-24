"""Centralized Logfire telemetry and OpenTelemetry instrumentation for Doubtless."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import logfire

from doubtless.config import (
    LOGFIRE_ENVIRONMENT,
    LOGFIRE_EXCLUDED_URLS,
    LOGFIRE_SEND_TO_LOGFIRE,
    LOGFIRE_TOKEN,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

_instrumented_services: set[str] = set()


def init_telemetry(
    service_name: str, app: FastAPI | None = None, *, force: bool = False
) -> None:
    """Initialize Logfire configuration and attach instrumentation to all subsystems."""
    if service_name in _instrumented_services and not force:
        if app is not None:
            # ponytail: ensure app is instrumented if passed in subsequent call
            try:
                logfire.instrument_fastapi(app, excluded_urls=LOGFIRE_EXCLUDED_URLS)
            except Exception as exc:  # noqa: BLE001
                logger.debug("FastAPI instrumentation skipped: %s", exc)
        return

    try:
        configure_kwargs: dict[str, Any] = {
            "service_name": service_name,
            "environment": LOGFIRE_ENVIRONMENT,
            "distributed_tracing": True,
            "inspect_arguments": False,
        }
        if LOGFIRE_TOKEN:
            configure_kwargs["token"] = LOGFIRE_TOKEN
        if LOGFIRE_SEND_TO_LOGFIRE is not None:
            configure_kwargs["send_to_logfire"] = LOGFIRE_SEND_TO_LOGFIRE

        logfire.configure(**configure_kwargs)

        # Core subsystem instrumentations
        logfire.instrument_pydantic_ai()
        logfire.instrument_sqlite3()
        # ponytail: omit redis to prevent Celery heartbeats (PUBLISH) spamming
        logfire.instrument_httpx()
        logfire.instrument_celery()

        if app is not None:
            logfire.instrument_fastapi(app, excluded_urls=LOGFIRE_EXCLUDED_URLS)

        _instrumented_services.add(service_name)
        logger.info("Logfire telemetry initialized for service: %s", service_name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to initialize Logfire telemetry: %s", exc)
