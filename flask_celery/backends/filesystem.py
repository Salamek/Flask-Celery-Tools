import errno
import os
import time
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from flask_celery.backends.base import LockBackend


class LockBackendFilesystem(LockBackend):
    LOCK_NAME = '{}.lock'

    def __init__(self, task_lock_backend_uri):
        super(LockBackendFilesystem, self).__init__(task_lock_backend_uri)
        self.log.warning('You are using filesystem locking backend which is good only for development env or for single'
                         ' task producer setup !')
        parsed_backend_uri = urlparse(task_lock_backend_uri)
        self.path = parsed_backend_uri.path
        try:
            os.makedirs(self.path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(self.path):
                pass
            else:
                raise

    def get_lock_path(self, task_identifier):
        return os.path.join(self.path, self.LOCK_NAME.format(task_identifier))

    def acquire(self, task_identifier, timeout):
        lock_path = self.get_lock_path(task_identifier)

        try:
            with open(lock_path, 'r') as fr:
                created = fr.read().strip()
                if not created:
                    raise IOError

                if int(time.time()) < (int(created) + timeout):
                    return False
                else:
                    raise IOError
        except IOError:
            with open(lock_path, 'w') as fw:
                fw.write(str(int(time.time())))
            return True

    def release(self, task_identifier):
        lock_path = self.get_lock_path(task_identifier)
        try:
            os.remove(lock_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def exists(self, task_identifier, timeout):
        lock_path = self.get_lock_path(task_identifier)
        try:
            with open(lock_path, 'r') as fr:
                created = fr.read().strip()
                if not created:
                    raise IOError

                if int(time.time()) < (int(created) + timeout):
                    return True
                else:
                    raise IOError
        except IOError:
            return False
