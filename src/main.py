from fastapi import FastAPI
from uvicorn import run
from src.downloader.router import router as downloader_router

app = FastAPI(
    title="FlowPipe API",
    description="API для извлечения метаданных и стриминга видео с YouTube.",
    openapi_tags=[
        {
            "name": "Загрузка (YouTube)",
            "description": "Эндпоинты для получения информации о видео и скачивания/стриминга в выбранном формате.",
        },
    ],
)
app.include_router(downloader_router)

if __name__ == '__main__':
    run("src.main:app", host="0.0.0.0", port=8000, reload=True)
