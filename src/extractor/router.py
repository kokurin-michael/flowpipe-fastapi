from fastapi.routing import APIRouter
from src.extractor.extractor import extract

router = APIRouter(tags=["Извлечение данных"])


@router.get('/extract', name='Извлечь данные из ссылки для скачивания')
def extract_handler(url: str):
    return extract(url)