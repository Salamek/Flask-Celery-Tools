"""SQLAlchemy backend."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from flask_celery.backends.base import LockBackend
from flask_celery.backends.database.models import Lock
from flask_celery.backends.database.sessions import SessionManager


class LockBackendDb(LockBackend):
    """Lock backend implemented on SQLAlchemy supporting multiple databases."""

    def __init__(self, task_lock_backend_uri: str) -> None:
        """LockBackendDb constructor.

        :param task_lock_backend_uri: URI
        """
        super().__init__(task_lock_backend_uri)
        self.task_lock_backend_uri = task_lock_backend_uri

    def result_session(self, session_manager: SessionManager | None = None) -> Session:
        """Return session.

        :param session_manager: session manager to use
        :return: session
        """
        if session_manager is None:
            session_manager = SessionManager()

        return session_manager.session_factory(self.task_lock_backend_uri)

    @staticmethod
    @contextmanager
    def session_cleanup(session: Session) -> Iterator[None]:
        """Cleanup session.

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
        """Acquire lock.

        :param task_identifier: task identifier
        :param timeout: lock timeout
        :return: bool
        """
        session = self.result_session()
        with self.session_cleanup(session):
            try:
                lock = Lock(task_identifier)
                session.add(lock)
                session.commit()
            except (IntegrityError, ProgrammingError):
                session.rollback()

                # task_id exists, lets check expiration date
                lock = session.query(Lock).\
                    filter(Lock.task_identifier == task_identifier).one()
                # Ensure lock.created is timezone-aware (SQLite stores naive datetimes)
                lock_created = lock.created.replace(tzinfo=UTC) if lock.created.tzinfo is None else lock.created
                difference = datetime.now(UTC) - lock_created
                if difference < timedelta(seconds=timeout):
                    return False
                lock.created = datetime.now(UTC)
                session.add(lock)
                session.commit()
                return True
            except Exception:
                session.rollback()
                raise
            else:
                return True

    def release(self, task_identifier: str) -> None:
        """Release lock.

        :param task_identifier: task identifier
        :return: None
        """
        session = self.result_session()
        with self.session_cleanup(session):
            session.query(Lock).filter(Lock.task_identifier == task_identifier).delete()
            session.commit()

    def exists(self, task_identifier: str, timeout: int) -> bool:
        """Check if lock exists and is valid.

        :param task_identifier: task identifier
        :param timeout: lock timeout
        :return: bool
        """
        session = self.result_session()
        with self.session_cleanup(session):
            lock = session.query(Lock)\
                .filter(Lock.task_identifier == task_identifier).first()
            if not lock:
                return False
            # Ensure lock.created is timezone-aware (SQLite stores naive datetimes)
            lock_created = lock.created.replace(tzinfo=UTC) if lock.created.tzinfo is None else lock.created
            difference = datetime.now(UTC) - lock_created
            if difference < timedelta(seconds=timeout):
                return True

        return False
