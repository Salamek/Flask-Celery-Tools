
import sqlalchemy as sa
from flask_celery.backends.database.sessions import LockModelBase
from datetime import datetime


class Lock(LockModelBase):

    __tablename__ = 'celeryd_lock'
    __table_args__ = {'sqlite_autoincrement': True}

    id = sa.Column(sa.Integer, sa.Sequence('lock_id_sequence'),
                   primary_key=True, autoincrement=True)
    task_identifier = sa.Column(sa.String(155), unique=True)
    created = sa.Column(sa.DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow, nullable=True)

    def __init__(self, task_identifier):
        self.task_identifier = task_identifier
