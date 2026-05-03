from pathlib import Path

from src.transcriber.transcriber import transcribe
from src.transcriber.models import WhisperModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_transcribe():
    transcribe(audio_file_path=PROJECT_ROOT / 'test_audio.m4a', models_folder_path=PROJECT_ROOT / 'whisper_models',
               model_name=WhisperModel.TURBO)


if __name__ == '__main__':
    test_transcribe()
