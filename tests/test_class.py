"""Test the Celery class."""

import pytest
from flask import Flask

from flask_celery import Celery


def test_multiple(flask_app: Flask) -> None:
    """Test attempted re-initialization of extension."""
    assert "celery" in flask_app.extensions

    with pytest.raises(ValueError, match=r"Already registered extension CELERY."):
        Celery(flask_app)


