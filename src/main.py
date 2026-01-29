from fastapi import FastAPI
from uvicorn import run
from src.downloader.router import router as downloader_router

app = FastAPI()
app.include_router(downloader_router)

if __name__ == '__main__':
    run("src.main:app", host="0.0.0.0", port=8000, reload=True)
