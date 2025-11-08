"""Test backend."""

import pytest

from flask_celery.backends.base import LockBackend
from flask_celery.lock_manager import select_lock_backend


def test_base_acquire() -> None:
    """Test NotImplemented."""
    lb = LockBackend("redis://127.0.0.1")
    with pytest.raises(NotImplementedError):
        lb.acquire("test", 0)


def test_base_release() -> None:
    """Test NotImplemented."""
    lb = LockBackend("redis://127.0.0.1")

    with pytest.raises(NotImplementedError):
        lb.release("test")


def test_base_exists() -> None:
    """Test NotImplemented."""
    lb = LockBackend("redis://127.0.0.1")

    with pytest.raises(NotImplementedError):
        lb.exists("test", 0)


def test_select_lock_backend_unknown() -> None:
    """Test NotImplemented."""
    with pytest.raises(NotImplementedError):
        select_lock_backend("not-implemented://127.0.0.1")
