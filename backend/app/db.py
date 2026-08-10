from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def secure_postgres_tables() -> None:
    """Keep the API as the only public data path when running on PostgreSQL/Supabase."""
    if engine.dialect.name != "postgresql":
        return
    table_names = [name for name in Base.metadata.tables if name.startswith("subscription_")]
    with engine.begin() as connection:
        roles = {
            role: bool(connection.scalar(text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}))
            for role in ("anon", "authenticated")
        }
        for table_name in table_names:
            quoted_table = table_name.replace('"', '""')
            connection.execute(text(f'ALTER TABLE public."{quoted_table}" ENABLE ROW LEVEL SECURITY'))
            for role, exists in roles.items():
                if exists:
                    connection.execute(text(f'REVOKE ALL ON TABLE public."{quoted_table}" FROM {role}'))
