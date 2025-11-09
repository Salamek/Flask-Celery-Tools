"""Tasks for tests."""
import flask
from celery import Task, shared_task

from flask_celery import single_instance


@shared_task(bind=True)
@single_instance
def add(_cls: Task, x: int, y: int) -> int:
    """Celery task: add numbers."""
    return x + y


@shared_task(bind=True)
@single_instance(include_args=True, lock_timeout=20)
def mul(_cls: Task, x: int, y: int) -> int:
    """Celery task: multiply numbers."""
    return x * y


@shared_task(bind=True)
@single_instance()
def sub(_cls: Task, x: int, y: int) -> int:
    """Celery task: subtract numbers."""
    return x - y


@shared_task(bind=True, time_limit=70)
@single_instance
def add2(_cls: Task, x: int, y: int) -> int:
    """Celery task: add numbers."""
    return x + y


@shared_task(bind=True, soft_time_limit=80)
@single_instance
def add3(_cls: Task, x: int, y: int) -> int:
    """Celery task: add numbers."""
    return x + y


@shared_task(name="celery.ping")
def ping() -> str:
    """Return simple pong."""
    return "pong"


@shared_task()
def in_context() -> bool:
    """Test if we are in flask app context."""
    return flask.has_app_context()
