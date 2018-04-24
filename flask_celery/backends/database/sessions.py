"""SQLAlchemy sessions."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

LOCK_MODEL_BASE = declarative_base()


class SessionManager(object):
    """Manage SQLAlchemy sessions."""

    def __init__(self):
        """Constructor."""
        self.prepared = False

    @staticmethod
    def get_engine(dburi):
        """
        Create engine.

        :param dburi: dburi
        :return: engine
        """
        return create_engine(dburi, poolclass=NullPool)

    def create_session(self, dburi):
        """
        Create session.

        :param dburi: dburi
        :return: session
        """
        engine = self.get_engine(dburi)
        return engine, sessionmaker(bind=engine)

    def prepare_models(self, engine):
        """
        Prepare models (create tables).

        :param engine: engine
        :return: None
        """
        if not self.prepared:
            LOCK_MODEL_BASE.metadata.create_all(engine)
            self.prepared = True

    def session_factory(self, dburi):
        """
        Session factory.

        :param dburi: dburi
        :return: engine, session
        """
        engine, session = self.create_session(dburi)
        self.prepare_models(engine)
        return session()
