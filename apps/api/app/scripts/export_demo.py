"""Export the seeded demo session to JSON and Markdown under ./exports/.

Ensures the demo session exists (seeding if necessary) and writes both formats.
"""

from __future__ import annotations

from pathlib import Path

from ..database import SessionLocal
from ..repositories import SqlAlchemySessionRepository
from ..seed import seed
from ..services.export_service import ExportService

SESSION_ID = "SESSION-DEMO"


def main() -> None:
    seed(if_empty=True)
    out = Path("exports")
    out.mkdir(exist_ok=True)
    with SessionLocal() as db:
        service = ExportService(SqlAlchemySessionRepository(db))
        for fmt, ext in (("json", "json"), ("markdown", "md")):
            content, _ = service.export(SESSION_ID, fmt)
            path = out / f"discovery_package.{ext}"
            path.write_text(content, encoding="utf-8")
            print(f"Wrote {path}")


if __name__ == "__main__":
    main()
