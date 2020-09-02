"""Configure tests."""

import os

import pytest
from flask import Flask
from flask_redis import Redis
from flask_sqlalchemy import SQLAlchemy

from flask_celery import Celery


@pytest.fixture()
def app_config():
    """Generate a Flask config dict with settings for a specific broker based on an environment variable.

    To be merged into app.config.

    :return: Flask config to be fed into app.config.update().
    :rtype: dict
    """
    config = {}

    all_env_variables = [
        os.environ.get('BROKER'),
        os.environ.get('RESULT'),
        os.environ.get('LOCK')
    ]

    for env in all_env_variables:
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

    if 'redis' in all_env_variables:
        config['REDIS_URL'] = backends['redis']
    elif 'redis_sock' in all_env_variables:
        # Since experts @redis decided to drop redis+socket:// schema a replace it with unix://
        # i now cant detect redis correctly so i must use old schema
        config['REDIS_URL'] = backends['redis_sock']

    if os.environ.get('RESULT') in ['mysql', 'postgres', 'sqlite']:
        config['CELERY_RESULT_BACKEND'] = 'db+' + config['CELERY_RESULT_BACKEND']
        config['SQLALCHEMY_DATABASE_URI'] = backends.get(os.environ.get('RESULT'))
        config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if os.environ.get('BROKER') in ['mysql', 'postgres', 'sqlite']:
        config['CELERY_BROKER_URL'] = 'sqla+' + config['CELERY_BROKER_URL']

    return config


@pytest.fixture()
def celery_app(flask_app):
    """Create celery app.

    :param flask_app: Created flask app
    """
    return flask_app.extensions['celery'].celery


@pytest.fixture()
def flask_app(app_config):
    """Create the Flask app context and initializes any extensions such as Celery, Redis, SQLAlchemy, etc.

    :param dict app_config: Partial Flask config dict from generate_config().

    :return: The Flask app instance.
    """
    flask_app = Flask(__name__)
    flask_app.config.update(app_config)
    flask_app.config['TESTING'] = True
    flask_app.config['CELERY_ACCEPT_CONTENT'] = ['pickle', 'json']

    if 'SQLALCHEMY_DATABASE_URI' in flask_app.config:
        db = SQLAlchemy(flask_app)
        db.engine.execute('DROP TABLE IF EXISTS celery_tasksetmeta;')
    elif 'REDIS_URL' in flask_app.config:
        redis = Redis(flask_app)
        redis.flushdb()

    Celery(flask_app)
    return flask_app
