from sqlmodel import SQLModel, create_engine, Session
from .config import settings

engine = create_engine(settings.database_url, echo=False)


def init_db():
    # ensure models are imported
    from . import models  # noqa: F401

    # Create all tables (no-op if exists)
    SQLModel.metadata.create_all(engine)

    # Best-effort миграции под SQLite: solo_level + user_id + role + max_questions
    with engine.begin() as conn:
        # MessageDB.solo_level
        cols = conn.exec_driver_sql("PRAGMA table_info('messagedb')").fetchall()
        if "solo_level" not in [c[1] for c in cols]:
            try:
                conn.exec_driver_sql("ALTER TABLE messagedb ADD COLUMN solo_level VARCHAR")
            except Exception:
                pass

        # SessionDB.user_id
        cols2 = conn.exec_driver_sql("PRAGMA table_info('sessiondb')").fetchall()
        existing_cols2 = [c[1] for c in cols2]
        if "user_id" not in existing_cols2:
            try:
                conn.exec_driver_sql("ALTER TABLE sessiondb ADD COLUMN user_id VARCHAR")
            except Exception:
                pass
        if "max_questions" not in existing_cols2:
            try:
                conn.exec_driver_sql("ALTER TABLE sessiondb ADD COLUMN max_questions INTEGER")
            except Exception:
                pass

        # UserDB.role
        cols3 = conn.exec_driver_sql("PRAGMA table_info('userdb')").fetchall()
        if "role" not in [c[1] for c in cols3]:
            try:
                conn.exec_driver_sql("ALTER TABLE userdb ADD COLUMN role VARCHAR DEFAULT 'student'")
            except Exception:
                pass


def get_session():
    with Session(engine) as session:
        yield session
