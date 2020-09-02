"""Tasks for tests."""

from celery import shared_task

from flask_celery import single_instance


@shared_task(bind=True)
@single_instance
def add(self, x, y):
    """Celery task: add numbers."""
    return x + y


@shared_task(bind=True)
@single_instance(include_args=True, lock_timeout=20)
def mul(self, x, y):
    """Celery task: multiply numbers."""
    return x * y


@shared_task(bind=True)
@single_instance()
def sub(self, x, y):
    """Celery task: subtract numbers."""
    return x - y


@shared_task(bind=True, time_limit=70)
@single_instance
def add2(self, x, y):
    """Celery task: add numbers."""
    return x + y


@shared_task(bind=True, soft_time_limit=80)
@single_instance
def add3(self, x, y):
    """Celery task: add numbers."""
    return x + y


@shared_task(name='celery.ping')
def ping():
    # type: () -> str
    """Simple task that just returns 'pong'."""
    return 'pong'
