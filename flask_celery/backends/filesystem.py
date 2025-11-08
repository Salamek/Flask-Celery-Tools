"""Filesystem backend."""

import time
from pathlib import Path
from urllib.parse import urlparse

from flask_celery.backends.base import LockBackend


class LockBackendFilesystem(LockBackend):
    """Lock backend implemented on local filesystem."""

    path: Path
    LOCK_NAME = "{}.lock"

    def __init__(self, task_lock_backend_uri: str) -> None:
        """LockBackendFilesystem constructor.

        :param task_lock_backend_uri: URI
        """
        super().__init__(task_lock_backend_uri)
        parsed_backend_uri = urlparse(task_lock_backend_uri)
        self.path = Path(parsed_backend_uri.path)
        self.path.mkdir(exist_ok=True)

    def get_lock_path(self, task_identifier: str) -> Path:
        """Return path to lock by task identifier.

        :param task_identifier: task identifier
        :return: str path to lock file
        """
        return self.path.joinpath(self.LOCK_NAME.format(task_identifier))

    def acquire(self, task_identifier: str, timeout: int) -> bool:
        """Acquire lock.

        :param task_identifier: task identifier.
        :param timeout: lock timeout
        :return: bool
        """
        lock_path = self.get_lock_path(task_identifier)

        try:
            with lock_path.open("r") as file_read:
                created = file_read.read().strip()
                if not created:
                    return True

                return not int(time.time()) < (int(created) + timeout)
        except OSError:
            with lock_path.open("w") as file_write:
                file_write.write(str(int(time.time())))
            return True

    def release(self, task_identifier: str) -> None:
        """Release lock.

        :param task_identifier: task identifier
        :return: None
        """
        lock_path = self.get_lock_path(task_identifier)
        lock_path.unlink(missing_ok=True)

    def exists(self, task_identifier: str, timeout: int) -> bool:
        """Check if lock exists and is valid.

        :param task_identifier: task identifier
        :param timeout: lock timeout
        :return: bool
        """
        lock_path = self.get_lock_path(task_identifier)
        try:
            with lock_path.open("r") as file_read:
                created = file_read.read().strip()
                if not created:
                    return False

                return int(time.time()) < (int(created) + timeout)
        except OSError:
            return False
