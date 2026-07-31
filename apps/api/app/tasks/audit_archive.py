from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def archive_audit_logs(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    current_month = now.strftime("%Y_%m")
    next_month = now.strftime("%Y_%m")

    partition_name = f"audit_logs_{current_month}"
    existing = await db.execute(
        text(f"SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = :name)"),
        {"name": partition_name},
    )
    exists = existing.scalar()

    if not exists:
        from calendar import monthrange
        year = now.year
        month = now.month
        _, last_day = monthrange(year, month)
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day + 1:02d}"

        await db.execute(
            text(
                f"""
                CREATE TABLE {partition_name} PARTITION OF audit_logs
                FOR VALUES FROM ('{start_date}') TO ('{end_date}');
                """
            )
        )

    return {"partition": partition_name, "created": not bool(exists)}