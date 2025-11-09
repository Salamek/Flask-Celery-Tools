
# Flask-Celery-Tools  
  
This is a fork of [Flask-Celery-Helper](https://github.com/Robpol86/Flask-Celery-Helper)  
  
Even though the [Flask documentation](http://flask.pocoo.org/docs/patterns/celery/) says Celery extensions are  
unnecessary now, I found that I still need an extension to properly use Celery in large Flask applications. Specifically  
I need an init_app() method to initialize Celery after I instantiate it.  
  
This extension also comes with a ``single_instance`` method.  
  
* Python PyPy, 3.11, 3.12 and 3.13 supported.
  
[![Tests](https://github.com/Salamek/Flask-Celery-Tools/actions/workflows/python-test.yml/badge.svg)](https://github.com/Salamek/Flask-Celery-Tools/actions/workflows/python-test.yml)
 
## Attribution  

Single instance decorator inspired by [Ryan Roemer](http://loose-bits.com/2010/10/distributed-task-locking-in-celery.html).  
  

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
def add_together(a: int, b: int) -> int:  
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

def create_app() -> Flask:
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
def add_together(a: int, b: int) -> int:
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
def sleep_one_second(a: int, b: int) -> int:
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
