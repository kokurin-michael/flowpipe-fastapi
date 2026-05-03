from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.converter.converter import check_ffmpeg
from src.database import init_db
from src.downloader.router import router as downloader_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_ffmpeg()
    init_db()
    yield


app = FastAPI(
    title="FlowPipe API",
    description="API для извлечения метаданных и стриминга видео с YouTube.",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Download",
            "description": "Эндпоинты для получения информации о видео и скачивания/стриминга в выбранном формате.",
        },
    ],
)
app.include_router(downloader_router)
