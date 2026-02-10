"""
Сущность записи о загруженном/загружаемом файле yt-dlp.

Хранит идентификатор задачи, прогресс и статус загрузки, путь к файлу,
метаданные (описание, расширение) и список превью (ThumbnailItem).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class YtDlpFile(Base):
    """
    Запись о задаче загрузки одного файла через yt-dlp.

    - **id** — уникальный идентификатор задачи (UUID hex).
    - **progress** — прогресс загрузки в процентах (0–100).
    - **status** — статус: pending | downloading | ready | failure.
    - **file_path** — абсолютный путь к скачанному файлу после успешной загрузки.
    - **description** — текст описания видео (из extract_info).
    - **extension** — расширение/контейнер файла (mp4, webm, m4a и т.д.).
    - **thumbnails** — список превью в виде JSON: [{"url": str, "width": int|null, "height": int|null}, ...].
    - **created_at** — время создания записи (UTC).
    """

    __tablename__ = "yt_dlp_file"
    __table_args__ = {"comment": "Задачи загрузки файлов через yt-dlp и их метаданные (описание, расширение, превью)."}

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True, comment="UUID задачи в hex")
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, comment="Прогресс загрузки 0–100%")
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, comment="pending | downloading | ready | failure")
    outtmpl: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="Путь к файлу после загрузки")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Описание видео из extract_info")
    extension: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="Расширение/контейнер: mp4, webm, m4a и т.д.")
    thumbnails: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="Список превью: [{url, width?, height?}, ...]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Время создания записи (UTC)",
    )
