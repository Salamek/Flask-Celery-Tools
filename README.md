
# Flask-Celery-Tools  
  
This is a fork of [Flask-Celery-Helper](https://github.com/Robpol86/Flask-Celery-Helper)  
  
Even though the [Flask documentation](http://flask.pocoo.org/docs/patterns/celery/) says Celery extensions are  
unnecessary now, I found that I still need an extension to properly use Celery in large Flask applications. Specifically  
I need an init_app() method to initialize Celery after I instantiate it.  
  
This extension also comes with a ``single_instance`` method.  
  
* Python PyPy, 3.6, 3.7 and 3.8 supported on Linux and OS X.
* Python 3.6, 3.7 and 3.8 supported on Windows (both 32 and 64 bit versions of Python).
  
[![Build Status Windows ](https://img.shields.io/appveyor/ci/Salamek/Flask-Celery-Tools/master.svg?style=flat-square&label=AppVeyor%20CI)](https://ci.appveyor.com/project/Salamek/Flask-Celery-Tools) [![Build Status](https://img.shields.io/travis/Salamek/Flask-Celery-Tools/master.svg?style=flat-square&label=Travis%20CI)](https://travis-ci.com/Salamek/Flask-Celery-Tools ) [![Coverage Status](https://img.shields.io/codecov/c/github/Salamek/Flask-Celery-Tools/master.svg?style=flat-square&label=Codecov)](https://codecov.io/gh/Salamek/Flask-Celery-Tools) [![Latest Version ](https://img.shields.io/pypi/v/Flask-Celery-Tools.svg?style=flat-square&label=Latest)](https://pypi.python.org/pypi/Flask-Celery-Tools)
 
## Attribution  

Single instance decorator inspired by [Ryan Roemer](http://loose-bits.com/2010/10/distributed-task-locking-in-celery.html).  
  
## Supported Libraries  
  
* [Flask](http://flask.pocoo.org/) 0.12 to 1.1.2
* [Redis](http://redis.io/) 3.2.6  to 3.5.3
* [Celery](http://www.celeryproject.org/) 3.1.11 to 4.4.7  
  
## Quickstart  

Install:  
  
```bash  
pip install Flask-Celery-Helper  
  ```
## Examples    
  
### Basic Example
  
```python  
# example.py  
from flask import Flask  
from flask_celery import Celery  

app = Flask('example')  
app.config['CELERY_BROKER_URL'] = 'redis://localhost'  
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost'  
app.config['CELERY_TASK_LOCK_BACKEND'] = 'redis://localhost'  
celery = Celery(app)  

@celery.task()  
def add_together(a, b):  
    return a + b  

if __name__ == '__main__':  
    result = add_together.delay(23, 42)  
    print(result.get())  
```
Run these two commands in separate terminals:

```bash
celery -A example.celery worker
python example.py
```
### Factory Example

```python
# extensions.py
from flask_celery import Celery

celery = Celery()
```

```python
# application.py
from flask import Flask
from extensions import celery

def create_app():
    app = Flask(__name__)
    app.config['CELERY_IMPORTS'] = ('tasks.add_together', )
    app.config['CELERY_BROKER_URL'] = 'redis://localhost'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost'
    app.config['CELERY_TASK_LOCK_BACKEND'] = 'redis://localhost'
    celery.init_app(app)
    return app
```

```python
# tasks.py
from extensions import celery

@celery.task()
def add_together(a, b):
    return a + b
```

```python
# manage.py
from application import create_app

app = create_app()
app.run()
```

### Single Instance Example

```python
# example.py
import time
from flask import Flask
from flask_celery import Celery, single_instance
from flask_redis import Redis

app = Flask('example')
app.config['REDIS_URL'] = 'redis://localhost'
app.config['CELERY_BROKER_URL'] = 'redis://localhost'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost'
app.config['CELERY_TASK_LOCK_BACKEND'] = 'redis://localhost'
celery = Celery(app)
Redis(app)

@celery.task(bind=True)
@single_instance
def sleep_one_second(a, b):
    time.sleep(1)
    return a + b

if __name__ == '__main__':
    task1 = sleep_one_second.delay(23, 42)
    time.sleep(0.1)
    task2 = sleep_one_second.delay(20, 40)
    results1 = task1.get(propagate=False)
    results2 = task2.get(propagate=False)
    print(results1)  # 65
    if isinstance(results2, Exception) and str(results2) == 'Failed to acquire lock.':
        print('Another instance is already running.')
    else:
        print(results2)  # Should not happen.
```

### Locking backends

Flask-Celery-Tools supports multiple locking backends you can use:

#### Filesystem

Filesystem locking backend is using file locks on filesystem where worker is running, WARNING this backend is not usable for distributed tasks!!!

#### Redis

Redis backend is using redis for storing task locks, this backend is good for distributed tasks.


#### Database (MariaDB, PostgreSQL, etc)

Database backend is using database supported by SqlAlchemy to store task locks, this backend is good for distributed tasks. Except sqlite database that have same limitations as filesystem backend.


## Changelog

This project adheres to [Semantic Versioning](http://semver.org/).

1.3.0 - 2020-11-03
------------------
    * Celery 5 support added

1.2.9 - 2020-11-03
------------------
    * Bump celery to version 4.4.7

1.2.7 - 2020-09-12
------------------
    * Set username for twine in CI release

1.2.6 - 2020-09-10
------------------
    * Fixed archlinux build

1.2.5 - 2020-09-10
------------------
    * Update dependencies
    * Fixed unittests

1.2.4 - 2018-11-03
------------------
    * Append celery_self if task is bound

1.1.0 - 2014-12-28
------------------

Added
    * Windows support.
    * `single_instance` supported on SQLite/MySQL/PostgreSQL in addition to Redis.

Changed
    * `CELERY_RESULT_BACKEND` no longer mandatory.
    * Breaking changes: `flask.ext.celery.CELERY_LOCK` moved to `flask.ext.celery._LockManagerRedis.CELERY_LOCK`.

1.0.0 - 2014-11-01
------------------

Added
    * Support for non-Redis backends.

0.2.2 - 2014-08-11
------------------

Added
    * Python 2.6 and 3.x support.

0.2.1 - 2014-06-18
------------------

Fixed
    * `single_instance` arguments with functools.

0.2.0 - 2014-06-18
------------------

Added
    * `include_args` argument to `single_instance`.

0.1.0 - 2014-06-01
------------------

* Initial release.
