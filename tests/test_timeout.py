"""Test single-instance lock timeout."""

import time
from types import TracebackType

import pytest
from celery import Celery, Task
from celery import Celery as CeleryClass

from flask_celery.exceptions import OtherInstanceError
from flask_celery.lock_manager import LockManager

from .tasks import add, add2, add3, mul


@pytest.mark.parametrize(("task", "timeout"), [
    (mul, 20), (add, 300), (add2, 70),
    (add3, 80),
])
def test_instances(celery_app: CeleryClass, task: Task, timeout: int) -> None:
    """Test task instances."""
    _ = celery_app
    manager_instance = []
    original_exit = LockManager.__exit__

    def new_exit(self: LockManager,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
        ) -> bool | None:
        manager_instance.append(self)
        return original_exit(self, exc_type, exc_val, exc_tb)
    LockManager.__exit__ = new_exit  # type: ignore[method-assign]
    task.apply_async(args=(4, 4)).get()
    LockManager.__exit__ = original_exit  # type: ignore[method-assign]
    assert timeout == manager_instance[0].timeout


@pytest.mark.parametrize(("key", "value"), [("task_time_limit", 200), ("task_soft_time_limit", 100)])
def test_settings(key: str, value: str | int, celery_app: Celery) -> None:
    """Test different Celery time limit settings."""
    celery_app.conf.update({key: value})
    manager_instance = []
    original_exit = LockManager.__exit__

    def new_exit(self: LockManager,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        manager_instance.append(self)
        return original_exit(self, exc_type, exc_val, exc_tb)
    LockManager.__exit__ = new_exit  # type: ignore[method-assign]
    tasks = [
        (mul, 20), (add, value), (add2, 70),
        (add3, 80),
    ]

    for task, timeout in tasks:
        task.apply_async(args=(4, 4)).get()
        assert manager_instance.pop().timeout == timeout
    LockManager.__exit__ = original_exit  # type: ignore[method-assign]

    celery_app.conf.update({key: None})


def test_expired(celery_app: Celery) -> None:
    """Test timeout expired task instances."""
    celery_app.conf.update({"task_time_limit": 5})
    manager_instance = []
    task = add
    original_exit = LockManager.__exit__

    def new_exit(
            self: LockManager,
            _exc_type: type[BaseException] | None,
            _exc_val: BaseException | None,
            _exc_tb: TracebackType | None,
    ) -> bool | None:
        manager_instance.append(self)
        return None
    LockManager.__exit__ = new_exit  # type: ignore[method-assign]

    # Run the task and don't remove the lock after a successful run.
    assert task.apply_async(args=(4, 4)).get() == 8
    LockManager.__exit__ = original_exit  # type: ignore[method-assign]

    # Run again, lock is still active so this should fail.
    with pytest.raises(OtherInstanceError):
        task.apply_async(args=(4, 4)).get()

    # Wait 5 seconds (per CELERYD_TASK_TIME_LIMIT), then re-run, should work.
    time.sleep(5)
    assert task.apply_async(args=(4, 4)).get() == 8
    celery_app.conf.update({"task_time_limit": None})
