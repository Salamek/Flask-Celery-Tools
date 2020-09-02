"""SQLAlchemy sessions."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

LockModelBase = declarative_base()


class SessionManager:
    """Manage SQLAlchemy sessions."""

    def __init__(self):
        """Constructor."""
        self.prepared = False

    @staticmethod
    def get_engine(db_uri: str):
        """
        Create engine.

        :param db_uri: dburi
        :return: engine
        """
        return create_engine(db_uri, poolclass=NullPool)

    def create_session(self, db_uri: str):
        """
        Create session.

        :param db_uri: dburi
        :return: session
        """
        engine = self.get_engine(db_uri)
        return engine, sessionmaker(bind=engine)

    def prepare_models(self, engine) -> None:
        """
        Prepare models (create tables).

        :param engine: engine
        :return: None
        """
        if not self.prepared:
            LockModelBase.metadata.create_all(engine)
            self.prepared = True

    def session_factory(self, db_uri):
        """
        Session factory.

        :param db_uri: dburi
        :return: engine, session
        """
        engine, session = self.create_session(db_uri)
        self.prepare_models(engine)
        return session()
