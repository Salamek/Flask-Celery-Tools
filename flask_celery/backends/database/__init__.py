
from flask_celery.backends.base import LockBackend
from contextlib import contextmanager
from flask_celery.backends.database.models import Lock
from flask_celery.backends.database.sessions import SessionManager
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta


class LockBackendDb(LockBackend):
    def __init__(self, task_lock_backend_uri):
        super(LockBackendDb, self).__init__(task_lock_backend_uri)
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

    def exists(self, task_identifier, timeout):
        session = self.result_session()
        with self.session_cleanup(session):
            lock = session.query(Lock).filter(Lock.task_identifier == task_identifier).first()
            if not lock:
                return False
            difference = datetime.utcnow() - lock.created
            if difference < timedelta(seconds=timeout):
                return True

        return False
