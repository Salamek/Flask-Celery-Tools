"""Flask Celery Helper."""

import tempfile
from collections.abc import Callable
from functools import partial, wraps
from pathlib import Path
from typing import TypeVar, overload

from celery import Celery as CeleryClass
from celery import Task, _state
from flask import Flask

from flask_celery.backends.base import LockBackend
from flask_celery.lock_manager import LockManager, select_lock_backend
from flask_celery.types import CelerySerializable

__author__ = "@Salamek"
__license__ = "MIT"
__version__ = "1.5.3"

CT = TypeVar("CT")


class _CeleryState:
    """Remember the configuration for the (celery, app) tuple. Modeled from SQLAlchemy."""

    def __init__(self, celery: CeleryClass, app: Flask) -> None:
        self.celery = celery
        self.app = app


# noinspection PyProtectedMember
class Celery(CeleryClass):  # type: ignore[misc]
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

    lock_backend: LockBackend|None

    def __init__(self, app: Flask|None=None) -> None:
        """If app argument provided then initialize celery using application config values.

        If no app argument provided you should do initialization later with init_app method.

        :param app: Flask application instance.
        """
        # Backup Celery app registration function.
        self.original_register_app = _state._register_app  # noqa: SLF001
        self.lock_backend = None
        # Upon Celery app registration attempt, do nothing.
        _state._register_app = lambda _: None  # noqa: SLF001
        super().__init__()
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Actual method to read celery settings from app configuration and initialize the celery instance.

        :param app: Flask application instance.
        """
        # Restore Celery app registration function.
        _state._register_app = self.original_register_app  # noqa: SLF001
        if not hasattr(app, "extensions"):
            app.extensions = {}
        if "celery" in app.extensions:
            msg = "Already registered extension CELERY."
            raise ValueError(msg)
        app.extensions["celery"] = _CeleryState(self, app)

        class FlaskTask(Task):  # type: ignore[misc]
            def __call__(self, *args: object, **kwargs: object) -> object:
                with app.app_context():
                    return self.run(*args, **kwargs)

        # Instantiate celery and read config.
        super().__init__(
            app.import_name,
            broker=app.config["CELERY_BROKER_URL"],
            task_cls = FlaskTask,
        )

        # Set filesystem lock backend as default when none is specified
        if "CELERY_TASK_LOCK_BACKEND" not in app.config:
            temp_path = Path(tempfile.gettempdir()).joinpath("celery_lock")
            app.config["CELERY_TASK_LOCK_BACKEND"] = f"file://{temp_path}"

        task_lock_backend_name = app.config.get("CELERY_TASK_LOCK_BACKEND")
        if not task_lock_backend_name:
            msg = "CELERY_TASK_LOCK_BACKEND was not provided"
            raise ValueError(msg)

        # Instantiate lock backend
        lock_backend_class = select_lock_backend(task_lock_backend_name)
        self.lock_backend = lock_backend_class(task_lock_backend_name)

        # Set result backend default.
        if "CELERY_RESULT_BACKEND" in app.config:
            self._preconf["CELERY_RESULT_BACKEND"] = app.config["CELERY_RESULT_BACKEND"]

        celery_config = {}
        for key, value in app.config.items():
            if key.startswith("CELERY"):
                celery_config[key.replace("CELERY_", "").lower()] = value

        self.conf.update(celery_config)


@overload
def single_instance(
        func: Callable[..., CT],
        lock_timeout: int|None=None,
        *,
        include_args:bool=False,
) -> Callable[..., CT]: ...

@overload
def single_instance(
        func: None=None,
        lock_timeout: int|None=None,
        *,
        include_args:bool=False,
) -> Callable[[Callable[..., CT]], Callable[..., CT]]: ...

def single_instance(
        func: Callable[..., CT]|None=None,
        lock_timeout: int|None=None,
        *,
        include_args:bool=False,
) -> Callable[..., CT] | Callable[[Callable[..., CT]], Callable[..., CT]]:
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
    def wrapped(celery_self: Task, *args: CelerySerializable, **kwargs: CelerySerializable) -> CT:
        """Wrapp Celery task, for single_instance()."""
        # Select the manager and get timeout.
        timeout = (
            lock_timeout or celery_self.soft_time_limit or celery_self.time_limit
            or celery_self.app.conf.get("task_soft_time_limit")
            or celery_self.app.conf.get("task_time_limit")
            or (60 * 5)
        )

        lock_manager = LockManager(
            celery_self.app.lock_backend,
            celery_self,
            timeout,
            args,
            kwargs,
            include_args=include_args,
        )

        # Lock and execute.
        with lock_manager:
            if celery_self.__bound__:
                modified_args = list(args)
                modified_args.insert(0, celery_self)
                return func(*modified_args, **kwargs)

            return func(*args, **kwargs)
    return wrapped
