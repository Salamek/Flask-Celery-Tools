"""Tests for the task_cls parameter on Celery and Celery.init_app()."""

import flask
from celery import Task
from flask import Flask

from flask_celery import Celery


def _make_flask_app(name: str) -> Flask:
    """Create a minimal Flask app for testing."""
    app = Flask(name)
    app.config["CELERY_BROKER_URL"] = "memory://"
    app.config["CELERY_RESULT_BACKEND"] = "cache+memory://"
    return app


def test_no_task_cls_defaults_to_task() -> None:
    """FlaskTask should be a subclass of base Task when no task_cls is given."""
    app = _make_flask_app("test_no_task_cls")
    celery = Celery(app)
    assert issubclass(celery.Task, Task)


def test_custom_task_cls_via_constructor() -> None:
    """FlaskTask should inherit from task_cls passed to Celery()."""

    class CustomTask(Task):  # type: ignore[misc]
        abstract = True

    app = _make_flask_app("test_custom_task_cls_constructor")
    celery = Celery(app, task_cls=CustomTask)
    assert issubclass(celery.Task, CustomTask)


def test_custom_task_cls_via_init_app() -> None:
    """FlaskTask should inherit from task_cls passed to init_app()."""

    class CustomTask(Task):  # type: ignore[misc]
        abstract = True

    app = _make_flask_app("test_custom_task_cls_init_app")
    celery = Celery()
    celery.init_app(app, task_cls=CustomTask)
    assert issubclass(celery.Task, CustomTask)


def test_constructor_task_cls_used_when_init_app_has_none() -> None:
    """task_cls from Celery() should be used when init_app() is called without one."""

    class CustomTask(Task):  # type: ignore[misc]
        abstract = True

    app = _make_flask_app("test_task_cls_stored_in_init")
    celery = Celery(task_cls=CustomTask)
    celery.init_app(app)
    assert issubclass(celery.Task, CustomTask)


def test_init_app_task_cls_overrides_constructor_task_cls() -> None:
    """task_cls passed to init_app() should take precedence over the one from Celery()."""

    class Task1(Task):  # type: ignore[misc]
        abstract = True

    class Task2(Task):  # type: ignore[misc]
        abstract = True

    app = _make_flask_app("test_task_cls_override")
    celery = Celery(task_cls=Task1)
    celery.init_app(app, task_cls=Task2)
    assert issubclass(celery.Task, Task2)
    assert not issubclass(celery.Task, Task1)


def test_custom_task_cls_attributes_accessible() -> None:
    """Custom task_cls methods and attributes should be accessible through FlaskTask."""

    class CustomTask(Task):  # type: ignore[misc]
        abstract = True
        custom_class_attr = "hello"

        def custom_method(self) -> str:
            return "from_custom"

    app = _make_flask_app("test_custom_task_cls_attrs")
    celery = Celery(app, task_cls=CustomTask)
    assert issubclass(celery.Task, CustomTask)
    assert celery.Task.custom_class_attr == "hello"

    instance = celery.Task()
    assert instance.custom_method() == "from_custom"


def test_custom_task_cls_flask_context_still_applied() -> None:
    """Flask app context should still be injected even with a custom task_cls."""

    class CustomTask(Task):  # type: ignore[misc]
        abstract = True

    app = _make_flask_app("test_custom_task_cls_context")
    app.config["CELERY_TASK_ALWAYS_EAGER"] = True
    app.config["CELERY_TASK_EAGER_PROPAGATES"] = True
    celery = Celery(app, task_cls=CustomTask)
    celery.set_current()

    @celery.task
    def check_context() -> bool:
        return flask.has_app_context()

    assert check_context.apply_async().get() is True


def test_multiple_apps_independent_task_cls() -> None:
    """Each app should use its own task_cls independently."""

    class Task1(Task):  # type: ignore[misc]
        abstract = True

    class Task2(Task):  # type: ignore[misc]
        abstract = True

    app1 = _make_flask_app("test_multi_app_task_cls_1")
    app2 = _make_flask_app("test_multi_app_task_cls_2")

    celery1 = Celery(app1, task_cls=Task1)
    celery2 = Celery(app2, task_cls=Task2)

    assert issubclass(celery1.Task, Task1)
    assert issubclass(celery2.Task, Task2)
    assert not issubclass(celery1.Task, Task2)
    assert not issubclass(celery2.Task, Task1)
