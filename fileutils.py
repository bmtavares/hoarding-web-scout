import csv
from dataclasses import asdict
import dataclasses
from datetime import datetime
import json
from pathlib import Path

from constants import AppFiles
from pagedata import PageData, PageHistory, PageSection


FILE_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
}


class HoardingJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        if isinstance(obj, PageSection):
            return vars(obj)
        if isinstance(obj, datetime):
            return str(obj)
        return super().default(obj)


def write_file(
    content: bytes, file_name: str, page: str, section: str, timestamp: datetime
) -> None:
    path: Path = Path(page)
    path = path / section / f"{timestamp.year}-{timestamp.month}-{timestamp.day}"
    path.mkdir(exist_ok=True, parents=True)

    final_file_name: str = (
        f"{timestamp.hour}h{timestamp.minute}m{timestamp.second}s{file_name}"
    )

    path = path / final_file_name

    with path.open("wb+") as f:
        f.write(content)


def read_pagedata() -> list[PageData]:
    data: dict

    def read(file: Path) -> dict:
        with file.open() as f:
            return json.load(f)

    def deserialize(data_dict: dict) -> list[PageData]:
        d: dict

        return [
            PageData(name=d["name"], sections=[PageSection(s) for s in d["sections"]])
            for d in data_dict
        ]

    if Path(AppFiles.WORKING_PAGES).exists():
        try:
            data = read(Path(AppFiles.WORKING_PAGES))
        except json.JSONDecodeError:
            data = read(Path(AppFiles.DEFAULT_PAGES))
    elif Path(AppFiles.DEFAULT_PAGES).exists():
        data = read(Path(AppFiles.DEFAULT_PAGES))
    else:
        raise FileNotFoundError

    return deserialize(data)


def write_pagedata(data: list[PageData]) -> None:
    path: Path = Path(AppFiles.WORKING_PAGES)
    if not path.exists():
        path.touch()

    with path.open("w") as f:
        f.write(json.dumps(data, cls=HoardingJSONEncoder))


def write_history(page: str, url: str, hash: str, timestamp: datetime) -> None:
    path: Path = Path(AppFiles.HISTORY)
    if not path.exists():
        path.touch()

    entry: PageHistory = PageHistory(page, url, hash, str(timestamp))

    dict = asdict(entry)

    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[k for k in dict])
        w.writerow(dict)


def write_page(
    name: str, content: str, timestamp: datetime, page_type: str = None
) -> None:
    path: Path = Path(name)
    path = path / page_type / f"{timestamp.year}-{timestamp.month}-{timestamp.day}"
    path.mkdir(exist_ok=True, parents=True)

    file_name: str = f"{timestamp.hour}h{timestamp.minute}m{timestamp.second}s.html"

    path = path / file_name

    with path.open("w+") as f:
        f.write(content)
