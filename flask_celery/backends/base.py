"""Lock backend."""

from logging import getLogger


class LockBackend:
    """Abstract class for implementation of LockBackend."""

    def __init__(self, task_lock_backend_uri: str):
        """
        Constructor.

        :param task_lock_backend_uri: URI
        """
        self.task_lock_backend_uri = task_lock_backend_uri
        self.log = getLogger('{}'.format(self.__class__.__name__))

    def acquire(self, task_identifier: str, timeout: int) -> bool:
        """
        Acquire lock.

        :param task_identifier: task identifier
        :param timeout: lock timeout
        :return: bool
        """
        raise NotImplementedError

    def release(self, task_identifier: str) -> None:
        """
        Release lock.

        :param task_identifier: task identifier
        :return: None
        """
        raise NotImplementedError

    def exists(self, task_identifier: str, timeout: int) -> bool:
        """
        Check if lock exists and is valid.

        :param task_identifier: task identifier
        :param timeout: lock timeout
        :return: bool
        """
        raise NotImplementedError
