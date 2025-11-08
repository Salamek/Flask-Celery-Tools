"""Collision tests."""

from types import TracebackType

import pytest
from celery import Celery as CeleryClass
from celery import Task

from flask_celery.exceptions import OtherInstanceError
from flask_celery.lock_manager import LockManager

from .tasks import add, mul, sub

PARAMS = [(add, 8), (mul, 16), (sub, 0)]


@pytest.mark.parametrize(("task", "expected"), PARAMS)
def test_basic(celery_app: CeleryClass, task: Task, expected: int) -> None:
    """Test no collision."""
    _ = celery_app
    assert expected == task.apply_async(args=(4, 4)).get()


@pytest.mark.parametrize(("task", "expected"), PARAMS)
def test_collision(celery_app: CeleryClass, task: Task, expected: int) -> None:
    """Test single-instance collision."""
    _ = celery_app
    manager_instance = []

    # First run the task and prevent it from removing the lock.
    def new_exit(self: LockManager,
         _exc_type: type[BaseException] | None,
         _exc_val: BaseException | None,
         _exc_tb: TracebackType | None,
     ) -> bool | None:
        manager_instance.append(self)
        return None
    original_exit = LockManager.__exit__
    LockManager.__exit__ = new_exit  # type: ignore[method-assign]
    assert expected == task.apply_async(args=(4, 4)).get()
    LockManager.__exit__ = original_exit  # type: ignore[method-assign]
    assert manager_instance[0].is_already_running is True

    # Now run it again.
    with pytest.raises(OtherInstanceError) as e:
        task.apply_async(args=(4, 4)).get()

    if manager_instance[0].include_args:
        assert str(e.value).startswith(f"Failed to acquire lock, {task.name}.args.")
    else:
        assert f"Failed to acquire lock, {task.name} already running." == str(e.value)
    assert manager_instance[0].is_already_running is True

    # Clean up.
    manager_instance[0].reset_lock()
    assert manager_instance[0].is_already_running is False

    # Once more.
    assert expected == task.apply_async(args=(4, 4)).get()


def test_include_args(celery_app: CeleryClass) -> None:
    """Test single-instance collision with task arguments taken into account."""
    _ = celery_app
    manager_instance = []
    task = mul

    # First run the tasks and prevent them from removing the locks.
    def new_exit(
        self: LockManager,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> bool | None:
        """Expect to be run twice."""
        manager_instance.append(self)
        return None
    original_exit = LockManager.__exit__
    LockManager.__exit__ = new_exit  # type: ignore[method-assign]
    assert task.apply_async(args=(4, 4)).get() == 16
    assert task.apply_async(args=(5, 4)).get() == 20
    LockManager.__exit__ = original_exit  # type: ignore[method-assign]
    assert manager_instance[0].is_already_running is True
    assert manager_instance[1].is_already_running is True

    # Now run them again.
    with pytest.raises(OtherInstanceError) as e:
        task.apply_async(args=(4, 4)).get()
    assert str(e.value).startswith("Failed to acquire lock, tests.tasks.mul.args.")
    assert manager_instance[0].is_already_running is True
    with pytest.raises(OtherInstanceError) as e:
        task.apply_async(args=(5, 4)).get()
    assert str(e.value).startswith("Failed to acquire lock, tests.tasks.mul.args.")
    assert manager_instance[1].is_already_running is True

    # Clean up.
    manager_instance[0].reset_lock()
    assert manager_instance[0].is_already_running is False
    manager_instance[1].reset_lock()
    assert manager_instance[1].is_already_running is False

    # Once more.
    assert task.apply_async(args=(4, 4)).get() == 16
    assert task.apply_async(args=(5, 4)).get() == 20
