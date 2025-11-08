"""Configure tests."""
import os
from pathlib import Path
from typing import NotRequired, TypedDict

import pytest
from celery import Celery as CeleryClass
from flask import Flask

try:
    from flask_redis import Redis as FlaskRedis
except ImportError:
    from flask_redis import FlaskRedis
# Suppress Celery's default app creation warnings
import warnings

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

from flask_celery import Celery

warnings.filterwarnings("ignore", message=".*default app.*")


class TestConfig(TypedDict):
    """Configuration dict def."""

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_LOCK_BACKEND: str
    REDIS_URL: NotRequired[str]
    SQLALCHEMY_DATABASE_URI: NotRequired[str]
    SQLALCHEMY_TRACK_MODIFICATIONS: NotRequired[bool]


def _create_flask_app() -> Flask:
    """Create and configure Flask app with Celery."""
    broker_backend_name = os.environ.get("BROKER")
    result_backend_name = os.environ.get("RESULT")
    lock_backend_name = os.environ.get("LOCK")

    if not broker_backend_name or not result_backend_name or not lock_backend_name:
        msg = "All required env variables must be set!"
        raise ValueError(msg)

    backends = {
        "rabbit": "amqp://guest:guest@localhost:5672//",
        "redis": "redis://localhost/1",
        "redis_sock": "redis+socket:///tmp/redis.sock",
        "filesystem": "file:///tmp/celery_lock",
        "mongo": "mongodb://user:pass@localhost/test",
        "couch": "couchdb://user:pass@localhost/test",
        "beanstalk": "beanstalk://user:pass@localhost/test",
        "iron": "ironmq://project:token@/test",
        "mysql": "mysql+pymysql://user:pass@localhost/flask_celery_helper_test",
        "postgres": "postgresql+pg8000://user1:pass@localhost/flask_celery_helper_test",
        "sqlite": f"sqlite:///{Path(__file__).resolve().parent / 'test_database.sqlite'}",
    }

    broker_backend = backends.get(broker_backend_name)
    result_backend = backends.get(result_backend_name)
    lock_backend = backends.get(lock_backend_name)

    if not broker_backend or not result_backend or not lock_backend:
        msg = "Invalid backend configuration"
        raise ValueError(msg)

    app = Flask(__name__)

    config: TestConfig = {
        "CELERY_BROKER_URL": broker_backend,
        "CELERY_RESULT_BACKEND": result_backend,
        "CELERY_TASK_LOCK_BACKEND": lock_backend,
    }

    if "redis" in (broker_backend_name, result_backend_name, lock_backend_name):
        config["REDIS_URL"] = backends["redis"]

    if result_backend_name in ["mysql", "postgres", "sqlite"]:
        config["CELERY_RESULT_BACKEND"] = "db+" + config["CELERY_RESULT_BACKEND"]
        config["SQLALCHEMY_DATABASE_URI"] = result_backend
        config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if broker_backend_name in ["mysql", "postgres", "sqlite"]:
        config["CELERY_BROKER_URL"] = "sqla+" + config["CELERY_BROKER_URL"]

    app.config.update(config)
    app.config["TESTING"] = True
    app.config["CELERY_BROKER_HEARTBEAT"] = 0
    app.config["CELERY_ACCEPT_CONTENT"] = ["pickle", "json"]
    app.config["CELERY_TASK_ALWAYS_EAGER"] = True
    app.config["CELERY_TASK_EAGER_PROPAGATES"] = True

    if "SQLALCHEMY_DATABASE_URI" in app.config:
        with app.app_context():
            db = SQLAlchemy(app)
            sql = "DROP TABLE IF EXISTS celery_tasksetmeta;"
            if hasattr(db.engine, "execute"):
                db.engine.execute(sql)
            else:
                db.session.execute(text(sql))
    elif "REDIS_URL" in app.config:
        redis = FlaskRedis(app)
        redis.flushdb()

    Celery(app)
    return app


# Create Flask app at module level - this happens BEFORE test collection
# ensuring @shared_task binds to the correct app
_flask_app_instance = _create_flask_app()
_celery_app = _flask_app_instance.extensions["celery"].celery

# Set as current/default BEFORE any other imports
_celery_app.set_current()
_celery_app.set_default()

# Now import tasks - they will bind to the configured app
from . import tasks  # noqa: E402, F401


@pytest.fixture(autouse=True)
def reset_celery_app() -> None:
    """Ensure celery app is current before each test."""
    # Re-set current app before each test in case it was changed
    _celery_app.set_current()


@pytest.fixture(scope="session")
def celery_app() -> CeleryClass:
    """Return the celery app instance."""
    if _flask_app_instance is None:
        msg = "Flask app not initialized"
        raise RuntimeError(msg)
    return _flask_app_instance.extensions["celery"].celery


@pytest.fixture(scope="session")
def flask_app() -> Flask:
    """Return the Flask app instance."""
    if _flask_app_instance is None:
        msg = "Flask app not initialized"
        raise RuntimeError(msg)
    return _flask_app_instance
