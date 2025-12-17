from __future__ import annotations

from sqlalchemy import MetaData, Table
from sqlalchemy.engine import Engine


class TableRegistry:
    def __init__(self, engine: Engine, schema: str = "public"):
        self.engine = engine
        self.schema = schema
        self._md = MetaData(schema=schema)
        self._cache: dict[str, Table] = {}

    def get(self, name: str) -> Table:
        if name not in self._cache:
            self._cache[name] = Table(name, self._md, autoload_with=self.engine)
        return self._cache[name]

    def clear_cache(self) -> None:
        self._cache.clear()
