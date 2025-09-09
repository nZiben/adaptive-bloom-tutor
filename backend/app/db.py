from sqlmodel import SQLModel, create_engine, Session
from .config import settings

engine = create_engine(settings.database_url, echo=False)


def init_db():
    # ensure models are imported
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    # Best-effort миграции под SQLite: solo_level + user_id
    with engine.begin() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info('messagedb')").fetchall()
        if "solo_level" not in [c[1] for c in cols]:
            try:
                conn.exec_driver_sql("ALTER TABLE messagedb ADD COLUMN solo_level VARCHAR")
            except Exception:
                pass

        cols2 = conn.exec_driver_sql("PRAGMA table_info('sessiondb')").fetchall()
        if "user_id" not in [c[1] for c in cols2]:
            try:
                conn.exec_driver_sql("ALTER TABLE sessiondb ADD COLUMN user_id VARCHAR")
            except Exception:
                pass


def get_session():
    with Session(engine) as session:
        yield session
