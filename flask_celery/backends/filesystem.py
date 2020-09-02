"""Filesystem backend."""

import errno
import os
import time
from urllib.parse import urlparse

from flask_celery.backends.base import LockBackend


class LockBackendFilesystem(LockBackend):
    """Lock backend implemented on local filesystem."""

    LOCK_NAME = '{}.lock'

    def __init__(self, task_lock_backend_uri: str):
        """
        Constructor.

        :param task_lock_backend_uri: URI
        """
        super().__init__(task_lock_backend_uri)
        parsed_backend_uri = urlparse(task_lock_backend_uri)
        self.path = parsed_backend_uri.path
        try:
            os.makedirs(self.path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(self.path):
                pass
            else:
                raise

    def get_lock_path(self, task_identifier: str) -> str:
        """
        Return path to lock by task identifier.

        :param task_identifier: task identifier
        :return: str path to lock file
        """
        return os.path.join(self.path, self.LOCK_NAME.format(task_identifier))

    def acquire(self, task_identifier: str, timeout: int) -> bool:
        """
        Acquire lock.

        :param task_identifier: task identifier.
        :param timeout: lock timeout
        :return: bool
        """
        lock_path = self.get_lock_path(task_identifier)

        try:
            with open(lock_path, 'r') as file_read:
                created = file_read.read().strip()
                if not created:
                    raise IOError

                if int(time.time()) < (int(created) + timeout):
                    return False
                raise IOError
        except IOError:
            with open(lock_path, 'w') as file_write:
                file_write.write(str(int(time.time())))
            return True

    def release(self, task_identifier: str) -> None:
        """
        Release lock.

        :param task_identifier: task identifier
        :return: None
        """
        lock_path = self.get_lock_path(task_identifier)
        try:
            os.remove(lock_path)
        except OSError as exception:
            if exception.errno != errno.ENOENT:
                raise

    def exists(self, task_identifier: str, timeout: int) -> bool:
        """
        Check if lock exists and is valid.

        :param task_identifier: task identifier
        :param timeout: lock timeout
        :return: bool
        """
        lock_path = self.get_lock_path(task_identifier)
        try:
            with open(lock_path, 'r') as file_read:
                created = file_read.read().strip()
                if not created:
                    raise IOError

                if int(time.time()) < (int(created) + timeout):
                    return True
                raise IOError
        except IOError:
            return False
