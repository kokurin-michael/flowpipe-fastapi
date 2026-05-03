from pathlib import Path
from src.converter.models import AudioFormat
import ffmpeg


def to_audio(file_path: Path, ext: AudioFormat) -> Path:
    output_path = file_path.with_suffix(f".{ext}")

    (
        ffmpeg
        .input(str(file_path))
        .output(str(output_path), vn=None, acodec="copy")
        .overwrite_output()
        .run(quiet=True)
    )

    return output_path


def check_ffmpeg() -> None:
    """Raise RuntimeError if the ffmpeg binary is not reachable."""
    try:
        ffmpeg.probe("", cmd="ffprobe")
    except ffmpeg.Error:
        pass
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Install it (https://ffmpeg.org) "
            "and make sure it is available on PATH."
        )
