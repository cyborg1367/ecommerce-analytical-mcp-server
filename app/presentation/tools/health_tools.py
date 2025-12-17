from __future__ import annotations

from sqlalchemy import select, func

from app.container import Container


def register(mcp, container: Container) -> None:
    @mcp.tool(
        title="DB ping",
        description="Connectivity check: current database/user/schema/server time.",
        tags={"health"},
        meta={"read": True},
        annotations={"readOnlyHint": True},
    )
    def db_ping() -> dict:
        with container.uow_factory() as uow:
            stmt = select(
                func.current_database().label("db"),
                func.current_user().label("usr"),
                func.current_schema().label("schema"),
                func.now().label("server_time"),
            )
            row = uow.session.execute(stmt).mappings().one()
            return dict(row)
