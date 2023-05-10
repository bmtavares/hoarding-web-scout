from dataclasses import dataclass
from datetime import datetime


class PageSection:
    name: str
    url: str
    last_hash: str
    last_update: datetime
    last_attempt: datetime

    def __init__(self, data: dict) -> None:
        self.name = data["name"]
        self.url = data["url"]
        self.last_hash = data.get("last_hash", None)
        self.last_update = (
            datetime.fromisoformat(data["last_update"]) if data["last_update"] else None
        )
        self.last_attempt = (
            datetime.fromisoformat(data["last_attempt"])
            if data["last_attempt"]
            else None
        )


class PageChangeBroadcast:
    page_name: str
    section_name: str
    timestamp: datetime
    file_count: int

    def __init__(self, page_name: str, section_name: str, timestamp: datetime) -> None:
        self.page_name = page_name
        self.section_name = section_name
        self.timestamp = timestamp
        self.file_count = 0

    def to_str(self):
        if self.file_count:
            return f"{self.section_name} of {self.page_name} with {self.file_count} new files at {self.timestamp.strftime('%d-%m %H:%M')}"
        else:
            return f"{self.section_name} of {self.page_name} at {self.timestamp.strftime('%d-%m %H:%M')}"


@dataclass
class PageData:
    name: str
    sections: list[PageSection]


@dataclass
class PageHistory:
    page: str
    section: str
    url: str
    hash: str
    timestamp: str
    lastmodified: str
