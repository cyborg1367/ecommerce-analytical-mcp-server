from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


class SqlAlchemyUnitOfWork:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.session: Session | None = None

    def __enter__(self):
        self.session = Session(self.engine, future=True, expire_on_commit=False)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
        finally:
            self.session.close()
