from __future__ import annotations

from pydantic import Field

from app.container import Container


def register(mcp, container: Container) -> None:
    @mcp.tool(
        title="Seed demo data",
        description="Insert realistic demo e-commerce data. Optionally truncates first. Requires ALLOW_WRITES=1.",
        tags={"seed", "demo"},
        meta={"write": True},
        annotations={"destructiveHint": True, "idempotentHint": False, "readOnlyHint": False},
    )
    def seed_demo_data(
        size: str = Field(default="small", description="small, medium, large"),
        reset_first: bool = Field(default=True, description="If true, TRUNCATE tables first."),
        seed: int = Field(default=42, description="Random seed for repeatable data."),
    ) -> dict:
        with container.uow_factory() as uow:
            return container.seed.seed_demo_data(uow.session, size=size, reset_first=reset_first, seed=seed)
