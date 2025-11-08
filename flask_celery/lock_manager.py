"""Lock manager."""
import hashlib
from logging import getLogger
from types import TracebackType
from urllib.parse import urlparse

from celery import Task

from flask_celery.backends.base import LockBackend
from flask_celery.backends.database import LockBackendDb
from flask_celery.backends.filesystem import LockBackendFilesystem
from flask_celery.backends.redis import LockBackendRedis
from flask_celery.exceptions import OtherInstanceError
from flask_celery.types import CelerySerializable


def select_lock_backend(task_lock_backend: str) -> type[LockBackend]:
    """Detect lock backend on task_lock_backend uri.

    :param task_lock_backend: uri
    :return: LockBackend
    """
    parsed_backend_uri = urlparse(task_lock_backend)
    scheme = str(parsed_backend_uri.scheme)

    if scheme.startswith("redis"):
        return LockBackendRedis

    if scheme.startswith(("sqla+", "db+", "mysql", "postgresql", "sqlite")):
        return LockBackendDb

    if scheme.startswith("file"):
        return LockBackendFilesystem

    msg = f"No backend found for {task_lock_backend}"
    raise NotImplementedError(msg)


class LockManager:
    """Lock manager."""

    def __init__(
            self,
            lock_backend: LockBackend,
            celery_self: Task,  # @TODO RENAME
            timeout: int,
            args: tuple[CelerySerializable, ...],
            kwargs: dict[str, CelerySerializable],
            *,
            include_args: bool,
    ) -> None:
        """Lock manager constructor.

        :param celery_self: From wrapped() within single_instance(). It is the `self` object specified in a binded
            Celery task definition (implicit first argument of the Celery task when @celery.task(bind=True) is used).
        :param int timeout: Lock's timeout value in seconds.
        :param bool include_args: If single instance should take arguments into account.
        :param iter args: The task instance's args.
        :param dict kwargs: The task instance's kwargs.
        """
        self.lock_backend = lock_backend
        self.celery_self = celery_self
        self.timeout = timeout
        self.include_args = include_args
        self.args = args
        self.kwargs = kwargs
        self.log = getLogger(f"{self.__class__.__name__}:{self.task_identifier}")

    @property
    def task_identifier(self) -> str:
        """Return the unique identifier (string) of a task instance."""
        task_id: str = self.celery_self.name
        if self.include_args:
            merged_args = str(self.args) + str([(k, self.kwargs[k]) for k in sorted(self.kwargs)])
            args_hash = hashlib.md5(merged_args.encode("utf-8"), usedforsecurity=False).hexdigest()
            task_id += f".args.{args_hash}"
        return task_id

    def __enter__(self) -> None:
        """Acquire lock if possible."""
        self.log.debug("Timeout %ds | Key %s", self.timeout, self.task_identifier)
        if not self.lock_backend.acquire(self.task_identifier, self.timeout):
            self.log.debug("Another instance is running.")
            msg = f"Failed to acquire lock, {self.task_identifier} already running."
            raise OtherInstanceError(msg)

        self.log.debug("Got lock, running.")

    def __exit__(self, exc_type: type[BaseException] | None, _value: BaseException | None, _traceback: TracebackType | None) -> bool | None:
        """Release lock."""
        if exc_type == OtherInstanceError:
            # Failed to get lock last time, not releasing.
            return None
        self.log.debug("Releasing lock.")
        self.lock_backend.release(self.task_identifier)
        return None

    @property
    def is_already_running(self) -> bool:
        """Return True if lock exists and has not timed out."""
        return self.lock_backend.exists(self.task_identifier, self.timeout)

    def reset_lock(self) -> None:
        """Remove the lock regardless of timeout."""
        self.lock_backend.release(self.task_identifier)
