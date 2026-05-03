from pathlib import Path

import ffmpeg
from whisper import load_model, load_audio, transcribe as whisper_transcribe
from src.transcriber.models import Transcription, Segment, Timestamp, WhisperModel


def transcribe(audio_file_path: Path, models_folder_path: Path, model_name: WhisperModel) -> Transcription:
    try:
        probe = ffmpeg.probe(str(audio_file_path))
        is_audio_file = any(stream['codec_type'] == 'audio' for stream in probe.get('streams', []))
    except ffmpeg.Error:
        is_audio_file = False

    if not is_audio_file:
        raise ValueError(f"Файл '{audio_file_path}' не является аудио файлом")

    model_path = models_folder_path / f"{model_name}.pt"
    if not model_path.exists():
        raise FileNotFoundError(f"Модель '{model_name}' не найдена по пути {model_path}")

    model = load_model(name=model_name, download_root=str(models_folder_path), in_memory=False)
    audio = load_audio(file=str(audio_file_path))
    result = whisper_transcribe(model=model, audio=audio, verbose=True)
    segments = [Segment(text=segment['text'], timestamp=Timestamp(start=segment['start'], end=segment['end'])) for
                segment in result['segments']]
    return Transcription(full_text=result['text'].lstrip(), segments=segments)
