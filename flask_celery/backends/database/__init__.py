"""SQLAlchemy backend."""

from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError, ProgrammingError

from flask_celery.backends.base import LockBackend
from flask_celery.backends.database.models import Lock
from flask_celery.backends.database.sessions import SessionManager


class LockBackendDb(LockBackend):
    """Lock backend implemented on SQLAlchemy supporting multiple databases."""

    def __init__(self, task_lock_backend_uri: str):
        """
        Constructor.

        :param task_lock_backend_uri: URI
        """
        super().__init__(task_lock_backend_uri)
        self.task_lock_backend_uri = task_lock_backend_uri

    def result_session(self, session_manager: SessionManager = SessionManager()):
        """
        Return session.

        :param session_manager: session manager to use
        :return: session
        """
        return session_manager.session_factory(self.task_lock_backend_uri)

    @staticmethod
    @contextmanager
    def session_cleanup(session) -> None:
        """
        Cleanup session.

        :param session: session
        :return: None
        """
        try:
            yield
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def acquire(self, task_identifier: str, timeout: int) -> bool:
        """
        Acquire lock.

        :param task_identifier: task identifier
        :param timeout: lock timeout
        :return: bool
        """
        session = self.result_session()
        with self.session_cleanup(session):
            try:
                lock = Lock(task_identifier)
                session.add(lock)  # pylint: disable=no-member
                session.commit()  # pylint: disable=no-member
                return True
            except (IntegrityError, ProgrammingError):
                session.rollback()  # pylint: disable=no-member

                # task_id exists, lets check expiration date
                lock = session.query(Lock).\
                    filter(Lock.task_identifier == task_identifier).one()  # pylint: disable=no-member
                difference = datetime.utcnow() - lock.created
                if difference < timedelta(seconds=timeout):
                    return False
                lock.created = datetime.utcnow()
                session.add(lock)  # pylint: disable=no-member
                session.commit()  # pylint: disable=no-member
                return True
            except Exception:
                session.rollback()  # pylint: disable=no-member
                raise

    def release(self, task_identifier: str) -> None:
        """
        Release lock.

        :param task_identifier: task identifier
        :return: None
        """
        session = self.result_session()
        with self.session_cleanup(session):
            session.query(Lock).filter(Lock.task_identifier == task_identifier).delete()  # pylint: disable=no-member
            session.commit()  # pylint: disable=no-member

    def exists(self, task_identifier: str, timeout: int) -> bool:
        """
        Check if lock exists and is valid.

        :param task_identifier: task identifier
        :param timeout: lock timeout
        :return: bool
        """
        session = self.result_session()
        with self.session_cleanup(session):
            lock = session.query(Lock)\
                .filter(Lock.task_identifier == task_identifier).first()  # pylint: disable=no-member
            if not lock:
                return False
            difference = datetime.utcnow() - lock.created
            if difference < timedelta(seconds=timeout):
                return True

        return False
