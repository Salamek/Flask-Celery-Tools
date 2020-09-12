"""Flask Celery Helper."""

import os
import tempfile
from functools import partial, wraps

from celery import _state, Celery as CeleryClass

from flask_celery.lock_manager import LockManager, select_lock_backend

__author__ = '@Salamek'
__license__ = 'MIT'
__version__ = '1.2.7'


class _CeleryState:
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
        super().__init__()
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
        super().__init__(app.import_name, broker=app.config['CELERY_BROKER_URL'])

        # Set filesystem lock backend as default when none is specified
        if 'CELERY_TASK_LOCK_BACKEND' not in app.config:
            temp_path = os.path.join(tempfile.gettempdir(), 'celery_lock')

            app.config['CELERY_TASK_LOCK_BACKEND'] = 'file://{}'.format(temp_path)
            self.log.warning(
                'No CELERY_TASK_LOCK_BACKEND has been configured, using filesystem locking as fallback, filesystem'
                ' locking have some limitations, read '
                'https://github.com/Salamek/Flask-Celery-Tools/blob/master/README.md#filesystem for more info')
        # Instantiate lock backend
        lock_backend_class = select_lock_backend(app.config.get('CELERY_TASK_LOCK_BACKEND'))
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
    def wrapped(celery_self, *args, **kwargs):  # noqa: D401
        """Wrapped Celery task, for single_instance()."""
        # Select the manager and get timeout.
        timeout = (
            lock_timeout or celery_self.soft_time_limit or celery_self.time_limit
            or celery_self.app.conf.get('CELERYD_TASK_SOFT_TIME_LIMIT')
            or celery_self.app.conf.get('CELERYD_TASK_TIME_LIMIT')
            or (60 * 5)
        )

        lock_manager = LockManager(
            celery_self.app.lock_backend,
            celery_self,
            timeout,
            include_args,
            args,
            kwargs
        )

        # Lock and execute.
        with lock_manager:
            if celery_self.__bound__:
                args = list(args)
                args.insert(0, celery_self)
            ret_value = func(*args, **kwargs)
        return ret_value
    return wrapped
