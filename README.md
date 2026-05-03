# FlowPipe FastAPI

## О проекте

**FlowPipe** — это backend на **FastAPI** для работы с видео **YouTube**: получение метаданных и списка форматов, запуск загрузки выбранного качества на сервер, отслеживание прогресса в **SQLite** и отдача готового файла клиенту (в том числе с поддержкой **HTTP Range** для паузы и перемотки).

Под капотом используются **yt-dlp** и при необходимости склейки дорожек — **ffmpeg**. Для части контента может понадобиться файл **cookies** (например, возрастные ограничения).

Дополнительно в репозитории есть модуль **transcriber** (OpenAI Whisper) для расшифровки аудио; в `main.py` сейчас подключён только сценарий загрузки с YouTube.

## Структура проекта

```text
flowpipe-fastapi/
├── src/
│   ├── main.py              # Приложение FastAPI, lifespan (ffmpeg, БД)
│   ├── config.py            # Настройки из .env (пути cookies, загрузок, БД)
│   ├── database.py          # SQLite, сессии SQLAlchemy
│   ├── downloader/          # Роуты и логика: extract_info, download, статус, файл
│   ├── downloader/downloader.py
│   ├── downloader/models.py
│   ├── converter/           # Проверка ffmpeg при старте; конвертация аудио
│   ├── transcriber/         # Логика Whisper (роутер в API не подключён)
│   └── entities/            # Модели БД (например, запись загрузки)
├── tests/                   # Тесты (pytest)
├── requirements.txt
└── README.md
```

## Требования

- **Python** 3.10+ (рекомендуется; зависимости включают torch/whisper)
- **ffmpeg** и **ffprobe** в `PATH` (проверяется при старте приложения)
- Файл **cookies** для YouTube по пути из настроек (по умолчанию `cookies.txt` в корне репозитория)

## Настройка (.env)

Необязательный файл `.env` в **корне проекта** (рядом с `requirements.txt`). Примеры переменных (имена в стиле pydantic-settings, обычно в верхнем регистре):

| Переменная       | По умолчанию           | Назначение                          |
|-----------------|------------------------|-------------------------------------|
| `COOKIE_FILE`   | `cookies.txt`          | Путь к cookies для yt-dlp           |
| `DOWNLOAD_DIR`  | `downloads`            | Каталог сохранения загрузок         |
| `DATABASE_FILE` | `flowpipe-database.db` | Файл SQLite                         |

Относительные пути считаются от корня проекта.

## Основные команды

### Окружение и зависимости

```bash
cd flowpipe-fastapi
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Запуск API

Из корня репозитория (чтобы корректно разрешались пути в `config`):

```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

- Документация OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Альтернативно: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Кратко про HTTP API

- `GET /extract_info?url=...` — метаданные и форматы
- `GET /download?url=...&video_format_id=...&audio_format_id=...` — старт загрузки, в ответе `download_id`
- `GET /download/status/{download_id}` — прогресс и статус
- `GET /download/file/{download_id}` — выдача файла (поддержка `Range`)

### Тесты

```bash
pytest tests/
```

Первый запуск может быть долгим из‑за зависимостей (torch и т.д.); часть интеграционных проверок может требовать сеть и валидный `cookies.txt`.
