"""Test the Celery class."""

import pytest

from flask_celery import Celery


class FakeApp(object):
    """Mock Flask application."""

    config = dict(
        CELERY_BROKER_URL='redis://localhost',
        CELERY_RESULT_BACKEND='redis://localhost',
        CELERY_TASK_LOCK_BACKEND='redis://localhost'
    )
    static_url_path = ''
    import_name = ''

    def register_blueprint(self, _):
        """Mock register_blueprint method."""
        pass


def test_multiple(flask_app):
    """Test attempted re-initialization of extension."""
    assert 'celery' in flask_app.extensions

    with pytest.raises(ValueError):
        Celery(flask_app)


def test_one_dumb_line():
    """For test coverage."""
    flask_app = FakeApp()
    Celery(flask_app)
    assert 'celery' in flask_app.extensions
