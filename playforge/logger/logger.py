from __future__ import annotations

import sys
from typing import Any

import structlog


_logger_configured = False


def configure_logging() -> None:
    global _logger_configured
    if _logger_configured:
        return

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.KeyValueRenderer(key_order=["event"]),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    _logger_configured = True


def get_logger(**context: Any):
    configure_logging()
    return structlog.get_logger().bind(**context)
