from dataclasses import asdict, dataclass
import sqlite3

from pagedata import PageHistory

DATABASE_NAME = "hoard.sqlite"

TABLE_DEFINITIONS = [
    "create table filehistory(page, section, name, url, hash, timestamp, lastmodified);",
    "create table pagehistory(page, section, url, hash, timestamp, lastmodified);",
]

DATE_FORMAT_HEADER = "%a, %d %b %Y %H:%M:%S %Z"


@dataclass
class FileHistory:
    page: str
    section: str
    name: str
    url: str
    hash: str
    timestamp: str
    lastmodified: str


def setup_db() -> None:
    with sqlite3.connect(DATABASE_NAME) as con:
        cur: sqlite3.Cursor = con.cursor()
        for table_def in TABLE_DEFINITIONS:
            try:
                cur.execute(table_def)
            except sqlite3.OperationalError:
                pass


def insert_page_history(entry: PageHistory) -> None:
    with sqlite3.connect(DATABASE_NAME) as con:
        cur: sqlite3.Cursor = con.cursor()
        cur.execute(
            """
            insert into pagehistory(page, section, url, hash, timestamp, lastmodified)
            values (:page, :section, :url, :hash, :timestamp, :lastmodified);
            """,
            asdict(entry),
        )


def insert_file_history(entry: FileHistory) -> None:
    with sqlite3.connect(DATABASE_NAME) as con:
        cur: sqlite3.Cursor = con.cursor()
        cur.execute(
            """
            insert into filehistory(page, section, name, url, hash, timestamp, lastmodified)
            values (:page, :section, :name, :url, :hash, :timestamp, :lastmodified);
            """,
            asdict(entry),
        )


def check_file_hash_count(hash: str) -> int:
    with sqlite3.connect(DATABASE_NAME) as con:
        cur: sqlite3.Cursor = con.cursor()
        res = cur.execute(
            """
            select count(*)
            from filehistory
            where hash=?;
            """,
            (hash,),
        ).fetchone()
        return res[0]


def check_file_hash_lastmodified(hash: str) -> str:
    with sqlite3.connect(DATABASE_NAME) as con:
        cur: sqlite3.Cursor = con.cursor()
        res = cur.execute(
            """
            select lastmodified
            from filehistory
            where hash=?
            order by lastmodified desc
            limit 1;
            """,
            (hash,),
        ).fetchone()
        if res:
            return res[0]
        return None


def check_file_name_lastmodified(name: str) -> str:
    with sqlite3.connect(DATABASE_NAME) as con:
        cur: sqlite3.Cursor = con.cursor()
        res = cur.execute(
            """
            select lastmodified
            from filehistory
            where name=?
            order by lastmodified desc
            limit 1;
            """,
            (name,),
        ).fetchone()
        if res:
            return res[0]
        return None


def check_file_entry_lastmodified(entry: FileHistory) -> str:
    with sqlite3.connect(DATABASE_NAME) as con:
        cur: sqlite3.Cursor = con.cursor()
        res = cur.execute(
            """
            select lastmodified
            from filehistory
            where page=? and section=? and name=? and hash=?
            order by lastmodified desc
            limit 1;
            """,
            (entry.page, entry.section, entry.name, entry.hash),
        ).fetchone()
        if res:
            return res[0]
        return None


def file_entry_exists(entry: FileHistory) -> bool:
    return check_file_entry_lastmodified(entry) == entry.lastmodified


if __name__ == "__main__":
    # setup_db()
    # insert_file_history(FileHistory('a','a','a','a','a','a'))
    foo = FileHistory(
        "det",
        "main_page",
        "LECM23PModelo2019solucao.pdf",
        "https://www.isel.pt/sites/default/files/Ingresso/TDET/LECM23PModelo2019solucao.pdf",
        "618ee903430da1f53c7295ff0f53ed9a",
        "Tue, 25 Apr 2023 00:03:06 GMT",
        "Thu, 16 Dec 2021 17:29:30 GMT",
    )
    # bar = check_file_hash_lastmodified('618ee903430da1f53c7295ff0f53ed9a')
    bar = check_file_entry_lastmodified(foo)
    print(bar == foo.lastmodified)
