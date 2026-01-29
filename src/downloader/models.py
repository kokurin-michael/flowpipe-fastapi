from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, List, Optional

class ExtractFormatKind(StrEnum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    THUMBNAIL = "THUMBNAIL"


@dataclass(slots=True)
class ExtractDataItem:
    format: ExtractFormatKind
    quality: str
    url: str
    headers: Optional[Dict[str, str]] = None


@dataclass(slots=True)
class ExtractMappedData:
    data: List[ExtractDataItem]
    description: Optional[str] = None