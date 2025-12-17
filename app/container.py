from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.config.settings import Settings
from app.infrastructure.db.engine import build_engine, normalize_sqlalchemy_dsn
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from app.infrastructure.db.reflection import SchemaReflection
from app.infrastructure.db.tables import TableRegistry

from app.application.services.schema_service import SchemaService
from app.application.services.sql_service import SqlService
from app.application.services.analytics_service import AnalyticsService
from app.application.services.ops_service import OpsService
from app.application.services.seed_service import SeedService


@dataclass(frozen=True)
class Container:
    settings: Settings
    uow_factory: Callable[[], SqlAlchemyUnitOfWork]

    schema: SchemaService
    sql: SqlService
    analytics: AnalyticsService
    ops: OpsService
    seed: SeedService


def build_container(settings: Settings) -> Container:
    dsn = normalize_sqlalchemy_dsn(settings.postgres_dsn)
    engine = build_engine(dsn)

    registry = TableRegistry(engine, schema="public")
    reflection = SchemaReflection(engine, schema="public")

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(engine)

    schema_svc = SchemaService(reflection)
    sql_svc = SqlService()
    analytics_svc = AnalyticsService(reflection, registry)
    ops_svc = OpsService(analytics_svc)
    seed_svc = SeedService(settings, reflection, registry)

    return Container(
        settings=settings,
        uow_factory=uow_factory,
        schema=schema_svc,
        sql=sql_svc,
        analytics=analytics_svc,
        ops=ops_svc,
        seed=seed_svc,
    )
