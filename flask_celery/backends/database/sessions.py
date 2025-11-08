"""SQLAlchemy sessions."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool


class LockModelBase(DeclarativeBase):
    """Custom base."""


class SessionManager:
    """Manage SQLAlchemy sessions."""

    def __init__(self) -> None:
        """SessionManager constructor."""
        self.prepared = False

    @staticmethod
    def get_engine(db_uri: str) -> Engine:
        """Create engine.

        :param db_uri: dburi
        :return: engine
        """
        return create_engine(db_uri, poolclass=NullPool)

    def create_session(self, db_uri: str) -> tuple[Engine, sessionmaker[Session]]:
        """Create session.

        :param db_uri: dburi
        :return: session
        """
        engine = self.get_engine(db_uri)
        return engine, sessionmaker(bind=engine)

    def prepare_models(self, engine: Engine) -> None:
        """Prepare models (create tables).

        :param engine: engine
        :return: None
        """
        if not self.prepared:
            LockModelBase.metadata.create_all(engine)
            self.prepared = True

    def session_factory(self, db_uri: str) -> Session:
        """Session factory.

        :param db_uri: dburi
        :return: engine, session
        """
        engine, session = self.create_session(db_uri)
        self.prepare_models(engine)
        return session()
