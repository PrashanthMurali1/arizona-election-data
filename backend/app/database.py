import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
(ROOT / "backend/local").mkdir(exist_ok=True)
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{ROOT / 'backend/local/elections.db'}"
)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def enable_fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass
