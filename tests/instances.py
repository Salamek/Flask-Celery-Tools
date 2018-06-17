"""Handle Flask and Celery application global-instances."""

import os

from flask import Flask
from flask_redis import Redis
from flask_sqlalchemy import SQLAlchemy

from flask_celery import Celery, single_instance


def generate_config():
    """Generate a Flask config dict with settings for a specific broker based on an environment variable.

    To be merged into app.config.

    :return: Flask config to be fed into app.config.update().
    :rtype: dict
    """
    config = dict()

    all_envs = [
        os.environ.get('BROKER'),
        os.environ.get('RESULT'),
        os.environ.get('LOCK')
    ]

    for env in all_envs:
        if not env:
            raise Exception('All required env variables must be set!')

    backends = {
        'rabbit': 'amqp://guest:guest@localhost:5672//',
        'redis': 'redis://localhost/1',
        'redis_sock': 'redis+socket:///tmp/redis.sock',
        'filesystem': 'file:///tmp/celery_lock',
        'mongo': 'mongodb://user:pass@localhost/test',
        'couch': 'couchdb://user:pass@localhost/test',
        'beanstalk': 'beanstalk://user:pass@localhost/test',
        'iron': 'ironmq://project:token@/test',
        'mysql': 'mysql+pymysql://user:pass@localhost/flask_celery_helper_test',
        'postgres': 'postgresql+pg8000://user1:pass@localhost/flask_celery_helper_test',
        'sqlite': 'sqlite:///{}'.format(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test_database.sqlite')
        )
    }

    config['CELERY_BROKER_URL'] = backends.get(os.environ.get('BROKER'))
    config['CELERY_RESULT_BACKEND'] = backends.get(os.environ.get('RESULT'))
    config['CELERY_TASK_LOCK_BACKEND'] = backends.get(os.environ.get('LOCK'))

    if 'redis' in all_envs:
        config['REDIS_URL'] = backends['redis']
    elif 'redis_sock' in all_envs:
        config['REDIS_URL'] = backends['redis_sock']

    if os.environ.get('RESULT') in ['mysql', 'postgres', 'sqlite']:
        config['CELERY_RESULT_BACKEND'] = 'db+' + config['CELERY_RESULT_BACKEND']
        config['SQLALCHEMY_DATABASE_URI'] = backends.get(os.environ.get('RESULT'))

    if os.environ.get('BROKER') in ['mysql', 'postgres', 'sqlite']:
        config['CELERY_BROKER_URL'] = 'sqla+' + config['CELERY_BROKER_URL']

    return config


def generate_context(config):
    """Create the Flask app context and initializes any extensions such as Celery, Redis, SQLAlchemy, etc.

    :param dict config: Partial Flask config dict from generate_config().

    :return: The Flask app instance.
    """
    flask_app = Flask(__name__)
    flask_app.config.update(config)
    flask_app.config['TESTING'] = True
    flask_app.config['CELERY_ACCEPT_CONTENT'] = ['pickle']

    if 'SQLALCHEMY_DATABASE_URI' in flask_app.config:
        db = SQLAlchemy(flask_app)
        db.engine.execute('DROP TABLE IF EXISTS celery_tasksetmeta;')
    elif 'REDIS_URL' in flask_app.config:
        redis = Redis(flask_app)
        redis.flushdb()

    Celery(flask_app)
    return flask_app


def get_flask_celery_apps():
    """Call generate_context() and generate_config().

    :return: First item is the Flask app instance, second is the Celery app instance.
    :rtype: tuple
    """
    config = generate_config()
    flask_app = generate_context(config=config)
    celery_app = flask_app.extensions['celery'].celery
    return flask_app, celery_app


app, celery = get_flask_celery_apps()


@celery.task(bind=True)
@single_instance
def add(x, y):
    """Celery task: add numbers."""
    return x + y


@celery.task(bind=True)
@single_instance(include_args=True, lock_timeout=20)
def mul(x, y):
    """Celery task: multiply numbers."""
    return x * y


@celery.task(bind=True)
@single_instance()
def sub(x, y):
    """Celery task: subtract numbers."""
    return x - y


@celery.task(bind=True, time_limit=70)
@single_instance
def add2(x, y):
    """Celery task: add numbers."""
    return x + y


@celery.task(bind=True, soft_time_limit=80)
@single_instance
def add3(x, y):
    """Celery task: add numbers."""
    return x + y
