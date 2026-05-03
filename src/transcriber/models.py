from dataclasses import dataclass
from enum import StrEnum


class WhisperModel(StrEnum):
    TINY = "tiny"
    TINY_EN = "tiny.en"
    BASE = "base"
    BASE_EN = "base.en"
    SMALL = "small"
    SMALL_EN = "small.en"
    MEDIUM = "medium"
    MEDIUM_EN = "medium.en"
    LARGE = "large"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"
    LARGE_V3_TURBO = "large-v3-turbo"
    TURBO = "turbo"

def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    return f"{hours:02}:{minutes:02}:{secs:02}.{millis:03}"

@dataclass(frozen=True)
class Timestamp:
    start: float
    end: float


@dataclass(frozen=True)
class Segment:
    text: str
    timestamp: Timestamp

    def prettier_timestamp(self) -> str:
        return f"{format_timestamp(self.timestamp.start)} --> {format_timestamp(self.timestamp.end)}"


@dataclass(frozen=True)
class Transcription:
    full_text: str
    segments: list[Segment]

    def full_text_with_timestamps(self) -> str:
        str_segments = [f"{segment.prettier_timestamp()}:{segment.text}" for segment in self.segments]
        return '\n'.join([str_segments[0]] + str_segments[1:]) if str_segments else ''
