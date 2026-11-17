"""Synchronous retries selected and bounded by the calling application."""

from .execution import retry
from .policy import RetryPolicy

__all__ = ["RetryPolicy", "retry"]
