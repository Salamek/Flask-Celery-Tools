from __future__ import absolute_import
import redis
from flask_celery.backends.base import LockBackend


class LockBackendRedis(LockBackend):
    CELERY_LOCK = '_celery.single_instance.{task_id}'

    def __init__(self, task_lock_backend_uri):
        super(LockBackendRedis, self).__init__(task_lock_backend_uri)
        self.redis_client = redis.StrictRedis.from_url(task_lock_backend_uri)

    def acquire(self, task_identifier, timeout):
        redis_key = self.CELERY_LOCK.format(task_id=task_identifier)
        lock = self.redis_client.lock(redis_key, timeout=timeout)
        return lock.acquire(blocking=False)

    def release(self, task_identifier):
        redis_key = self.CELERY_LOCK.format(task_id=task_identifier)
        self.redis_client.delete(redis_key)

    def exists(self, task_identifier, timeout):
        redis_key = self.CELERY_LOCK.format(task_id=task_identifier)
        return self.redis_client.exists(redis_key)

