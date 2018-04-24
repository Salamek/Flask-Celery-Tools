from logging import getLogger


class LockBackend(object):
    def __init__(self, task_lock_backend_uri):
        self.log = getLogger('{}'.format(self.__class__.__name__))

    def acquire(self, task_identifier, timeout):
        raise NotImplementedError

    def release(self, task_identifier):
        raise NotImplementedError

    def exists(self, task_identifier, timeout):
        raise NotImplementedError
