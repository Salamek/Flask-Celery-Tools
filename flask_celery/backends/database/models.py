"""SQLALchemy models."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, Sequence, String
from sqlalchemy.orm import Mapped, mapped_column

from flask_celery.backends.database.sessions import LockModelBase


class Lock(LockModelBase):
    """Model defying table in sqlalchemy database."""

    __tablename__ = "celeryd_lock"
    __table_args__ = ({"sqlite_autoincrement": True}, )

    id: Mapped[int] = mapped_column(Integer, Sequence("lock_id_sequence"), primary_key=True, autoincrement=True)
    task_identifier: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=True,
    )

    def __init__(self, task_identifier: str) -> None:
        """Lock constructor.

        :param task_identifier: task identifier
        """
        self.task_identifier = task_identifier
