
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker

LockModelBase = declarative_base()


class SessionManager(object):
    """Manage SQLAlchemy sessions."""

    def __init__(self):
        self.prepared = False

    def get_engine(self, dburi):
        return create_engine(dburi, poolclass=NullPool)

    def create_session(self, dburi):
        engine = self.get_engine(dburi)
        return engine, sessionmaker(bind=engine)

    def prepare_models(self, engine):
        if not self.prepared:
            LockModelBase.metadata.create_all(engine)
            self.prepared = True

    def session_factory(self, dburi):
        engine, session = self.create_session(dburi)
        self.prepare_models(engine)
        return session()