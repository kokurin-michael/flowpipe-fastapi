from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, List, Optional


class ExtractFormatEnum(StrEnum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    THUMBNAIL = "THUMBNAIL"


@dataclass(slots=True)
class ExtractDataItem:
    format: ExtractFormatEnum
    quality: str
    url: str
    headers: Optional[Dict[str, str]] = None


@dataclass(slots=True)
class ExtractData:
    data: List[ExtractDataItem]
    description: Optional[str] = None


class UrlOwnerEnum(StrEnum):
    YOUTUBE = "YOUTUBE"
