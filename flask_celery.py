"""Celery support for Flask without breaking PyCharm inspections.

https://github.com/Robpol86/Flask-Celery-Helper
https://pypi.python.org/pypi/Flask-Celery-Helper
"""

import hashlib
import redis
from sqlalchemy import create_engine
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import partial, wraps
from logging import getLogger

from celery import _state, Celery as CeleryClass

__author__ = '@Robpol86'
__license__ = 'MIT'
__version__ = '1.1.0'


class OtherInstanceError(Exception):
    """Raised when Celery task is already running, when lock exists and has not timed out."""

    pass


class _LockBackend(object):

    def acquire(self, task_identifier, timeout):
        raise NotImplementedError

    def release(self, task_identifier):
        raise NotImplementedError

    def exists(self, task_identifier):
        raise NotImplementedError


class _LockBackendRedis(_LockBackend):
    CELERY_LOCK = '_celery.single_instance.{task_id}'

    def __init__(self, task_lock_backend_uri):
        self.redis_client = redis.StrictRedis.from_url(task_lock_backend_uri)

    def acquire(self, task_identifier, timeout):
        redis_key = self.CELERY_LOCK.format(task_id=task_identifier)
        lock = self.redis_client.lock(redis_key, timeout=timeout)
        return lock.acquire(blocking=False)

    def release(self, task_identifier):
        redis_key = self.CELERY_LOCK.format(task_id=task_identifier)
        self.redis_client.delete(redis_key)

    def exists(self, task_identifier):
        redis_key = self.CELERY_LOCK.format(task_id=task_identifier)
        return self.redis_client.exists(redis_key)


LockModelBase = declarative_base()


class Lock(LockModelBase):

    __tablename__ = 'celeryd_lock'
    __table_args__ = {'sqlite_autoincrement': True}

    id = sa.Column(sa.Integer, sa.Sequence('lock_id_sequence'),
                   primary_key=True, autoincrement=True)
    task_identifier = sa.Column(sa.String(155), unique=True)
    created = sa.Column(sa.DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow, nullable=True)

    def __init__(self, task_id):
        self.task_id = task_id

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'date_done': self.date_done,
        }


class SessionManager(object):
    """Manage SQLAlchemy sessions."""

    def __init__(self):
        self.prepared = False

    def get_engine(self, dburi):
        return create_engine(dburi, poolclass=NullPool)

    def create_session(self, dburi):
        engine = self.get_engine(dburi)
        return engine, sessionmaker(bind=engine)

    def prepare_models(self, engine):
        if not self.prepared:
            LockModelBase.metadata.create_all(engine)
            self.prepared = True

    def session_factory(self, dburi):
        engine, session = self.create_session(dburi)
        self.prepare_models(engine)
        return session()


class _LockBackendDb(_LockBackend):
    def __init__(self, task_lock_backend_uri):
        self.task_lock_backend_uri = task_lock_backend_uri

    def result_session(self, session_manager=SessionManager()):
        return session_manager.session_factory(self.task_lock_backend_uri)

    @contextmanager
    def session_cleanup(self, session):
        try:
            yield
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def acquire(self, task_identifier, timeout):
        session = self.result_session()
        with self.session_cleanup(session):
            try:
                lock = Lock(task_identifier)
                session.add(lock)
                session.commit()
                return True
            except IntegrityError:
                session.rollback()

                # task_id exists, lets check expiration date
                lock = session.query(Lock).filter(Lock.task_identifier == task_identifier).one()
                difference = datetime.utcnow() - lock.created
                if difference < timedelta(seconds=timeout):
                    return False
                lock.created = datetime.utcnow()
                session.add(lock)
                session.commit()
                return True
            except:
                session.rollback()
                raise

    def release(self, task_identifier):
        session = self.result_session()
        with self.session_cleanup(session):
            session.query(Lock).filter(Lock.task_identifier == task_identifier).delete()
            session.commit()

    def exists(self, task_identifier):
        session = self.result_session()
        with self.session_cleanup(session):
            return session.query(Lock).filter(Lock.task_identifier == task_identifier).count() > 1


class _LockManager(object):
    """Base class for other lock managers."""

    def __init__(self, lock_backend, celery_self, timeout, include_args, args, kwargs):
        """May raise NotImplementedError if the Celery backend is not supported.

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
        self.log = getLogger('{0}:{1}'.format(self.__class__.__name__, self.task_identifier))

    @property
    def task_identifier(self):
        """Return the unique identifier (string) of a task instance."""
        task_id = self.celery_self.name
        if self.include_args:
            merged_args = str(self.args) + str([(k, self.kwargs[k]) for k in sorted(self.kwargs)])
            task_id += '.args.{0}'.format(hashlib.md5(merged_args.encode('utf-8')).hexdigest())
        return task_id

    def __enter__(self):
        self.log.debug('Timeout %ds | Key %s', self.timeout, self.task_identifier)
        if not self.lock_backend.acquire(self.task_identifier, self.timeout):
            self.log.debug('Another instance is running.')
            raise OtherInstanceError('Failed to acquire lock, {0} already running.'.format(self.task_identifier))
        else:
            self.log.debug('Got lock, running.')

    def __exit__(self, exc_type, *_):
        if exc_type == OtherInstanceError:
            # Failed to get lock last time, not releasing.
            return
        self.log.debug('Releasing lock.')
        self.lock_backend.release(self.task_identifier)

    @property
    def is_already_running(self):
        """Return True if lock exists and has not timed out."""
        return self.lock_backend.exists(self.task_identifier)

    def reset_lock(self):
        """Removed the lock regardless of timeout."""
        self.lock_backend.release(self.task_identifier)


def _select_lock_backend(task_lock_backend):
    if 'redis' in task_lock_backend:
        lock_manager = _LockBackendRedis
    elif task_lock_backend.startswith('db') or task_lock_backend.startswith('database'):
        lock_manager = _LockBackendDb
    else:
        raise NotImplementedError
    return lock_manager


class _CeleryState(object):
    """Remember the configuration for the (celery, app) tuple. Modeled from SQLAlchemy."""

    def __init__(self, celery, app):
        self.celery = celery
        self.app = app


# noinspection PyProtectedMember
class Celery(CeleryClass):
    """Celery extension for Flask applications.

    Involves a hack to allow views and tests importing the celery instance from extensions.py to access the regular
    Celery instance methods. This is done by subclassing celery.Celery and overwriting celery._state._register_app()
    with a lambda/function that does nothing at all.

    That way, on the first super() in this class' __init__(), all of the required instance objects are initialized, but
    the Celery application is not registered. This class will be initialized in extensions.py but at that moment the
    Flask application is not yet available.

    Then, once the Flask application is available, this class' init_app() method will be called, with the Flask
    application as an argument. init_app() will again call celery.Celery.__init__() but this time with the
    celery._state._register_app() restored to its original functionality. in init_app() the actual Celery application is
    initialized like normal.
    """

    def __init__(self, app=None):
        """If app argument provided then initialize celery using application config values.

        If no app argument provided you should do initialization later with init_app method.

        :param app: Flask application instance.
        """
        self.original_register_app = _state._register_app  # Backup Celery app registration function.
        self.lock_backend = None
        _state._register_app = lambda _: None  # Upon Celery app registration attempt, do nothing.
        super(Celery, self).__init__()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Actual method to read celery settings from app configuration and initialize the celery instance.

        :param app: Flask application instance.
        """
        _state._register_app = self.original_register_app  # Restore Celery app registration function.
        if not hasattr(app, 'extensions'):
            app.extensions = dict()
        if 'celery' in app.extensions:
            raise ValueError('Already registered extension CELERY.')
        app.extensions['celery'] = _CeleryState(self, app)

        # Instantiate celery and read config.
        super(Celery, self).__init__(app.import_name, broker=app.config['CELERY_BROKER_URL'])

        # Instantiate lock backend
        lock_backend_class = _select_lock_backend(app.config.get('CELERY_TASK_LOCK_BACKEND'))
        self.lock_backend = lock_backend_class(app.config.get('CELERY_TASK_LOCK_BACKEND'))

        # Set result backend default.
        if 'CELERY_RESULT_BACKEND' in app.config:
            self._preconf['CELERY_RESULT_BACKEND'] = app.config['CELERY_RESULT_BACKEND']

        self.conf.update(app.config)
        task_base = self.Task

        # Add Flask app context to celery instance.
        class ContextTask(task_base):
            def __call__(self, *_args, **_kwargs):
                with app.app_context():
                    return task_base.__call__(self, *_args, **_kwargs)
        setattr(ContextTask, 'abstract', True)
        setattr(self, 'Task', ContextTask)


def single_instance(func=None, lock_timeout=None, include_args=False):
    """Celery task decorator. Forces the task to have only one running instance at a time.

    Use with binded tasks (@celery.task(bind=True)).

    Modeled after:
    http://loose-bits.com/2010/10/distributed-task-locking-in-celery.html
    http://blogs.it.ox.ac.uk/inapickle/2012/01/05/python-decorators-with-optional-arguments/

    Written by @Robpol86.

    :raise OtherInstanceError: If another instance is already running.

    :param function func: The function to decorate, must be also decorated by @celery.task.
    :param int lock_timeout: Lock timeout in seconds plus five more seconds, in-case the task crashes and fails to
        release the lock. If not specified, the values of the task's soft/hard limits are used. If all else fails,
        timeout will be 5 minutes.
    :param bool include_args: Include the md5 checksum of the arguments passed to the task in the Redis key. This allows
        the same task to run with different arguments, only stopping a task from running if another instance of it is
        running with the same arguments.
    """
    if func is None:
        return partial(single_instance, lock_timeout=lock_timeout, include_args=include_args)

    @wraps(func)
    def wrapped(celery_self, *args, **kwargs):
        """Wrapped Celery task, for single_instance()."""
        # Select the manager and get timeout.
        timeout = (
            lock_timeout or celery_self.soft_time_limit or celery_self.time_limit
            or celery_self.app.conf.get('CELERYD_TASK_SOFT_TIME_LIMIT')
            or celery_self.app.conf.get('CELERYD_TASK_TIME_LIMIT')
            or (60 * 5)
        )

        lock_manager = _LockManager(
            celery_self.app.lock_backend,
            celery_self,
            timeout,
            include_args,
            args,
            kwargs
        )

        # Lock and execute.
        with lock_manager:
            ret_value = func(*args, **kwargs)
        return ret_value
    return wrapped
