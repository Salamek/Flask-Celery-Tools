"""Exceptions."""


class OtherInstanceError(Exception):
    """Raised when Celery task is already running, when lock exists and has not timed out."""
