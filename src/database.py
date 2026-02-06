from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import get_settings

_settings = get_settings()
_connect_args = {}
if _settings.database_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    _settings.database_url,
    connect_args=_connect_args,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    """Создаёт таблицы в БД (если их ещё нет). Создаёт родительскую папку для файла БД при необходимости."""
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_session():
    """Генератор сессии для Depends(FastAPI). Закрывает сессию после запроса."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
