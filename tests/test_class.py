"""Test the Celery class."""

import pytest
from celery import Celery as CeleryClass
from flask import Flask

from flask_celery import Celery

from .tasks import in_context


def test_multiple(flask_app: Flask) -> None:
    """Test attempted re-initialization of extension."""
    assert "celery" in flask_app.extensions

    with pytest.raises(ValueError, match=r"Already registered extension CELERY."):
        Celery(flask_app)


def test_in_context(celery_app: CeleryClass) -> None:
    """Test task running in flask app context."""
    _ = celery_app
    assert in_context.apply_async().get()
