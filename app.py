from datetime import datetime
import logging
import math
import os
import pathlib
import sys
import time
import hashlib
import requests
from bs4 import BeautifulSoup as bs, ResultSet, Tag
import telegram
import fileutils
import random
import broadcasts
from dotenv import load_dotenv
import asyncio
import datautils
from urllib.parse import urlparse

from pagedata import PageChangeBroadcast, PageData, PageSection


def scout_change(pd: PageData, ps: PageSection) -> PageChangeBroadcast | None:
    history_entry: PageChangeBroadcast = None

    try:
        rsp: requests.Response = request_content(ps.url)
        soup: bs = bs(rsp.text, "html.parser").select_one("div#content")

        current_hash = generate_page_hash(soup)
        if diff_page_data(ps, current_hash):
            logger.info(f"Page {ps.name} of {pd.name} has changed! Recording..")
            on_change_detected(pd, ps, rsp, current_hash)
            history_entry = PageChangeBroadcast(
                pd.name,
                ps.name,
                datetime.strptime(
                    rsp.headers.get("date"), datautils.DATE_FORMAT_HEADER
                ),
            )

        file_links: list[str] = find_files(soup)

        if file_links:
            count: int = download_and_check_files(file_links, pd, ps)
            if count:
                logger.info(f"Page {ps.name} of {pd.name} has {count} new files!")
                if not history_entry:
                    history_entry = PageChangeBroadcast(
                        pd.name,
                        ps.name,
                        datetime.strptime(
                            rsp.headers.get("date"), datautils.DATE_FORMAT_HEADER
                        ),
                    )
                history_entry.file_count = count

    except requests.exceptions.RequestException:
        logger.error(f"Could not fetch page {ps.name} of {pd.name}")

    return history_entry


def transform_refs(ref: str) -> str:
    """
    Discard 'mailto:' links and add full location when needed.

    :ref - url to check
    """
    url = urlparse(ref)
    if url.scheme:
        return None
    if url.netloc != "www.isel.pt":
        return f"https://www.isel.pt{url.path}"
    return ref


def find_files(soup: bs) -> list[str]:
    anchor_elements: ResultSet[Tag] = soup.select("a[href][rel*='noopener']")
    links: list[str] = list(
        map(transform_refs, [tag.attrs.get("href") for tag in anchor_elements])
    )
    return links


def download_and_check_files(links: list[str], pd: PageData, ps: PageSection) -> int:
    download_count: int = 0
    for link in links:
        if link:
            head: requests.Response = requests.head(link)
            if head.status_code == 200:
                file_name: str = link.split("/")[-1]
                # stored_last_modified: str = datautils.check_file_name_lastmodified(
                #     file_name
                # )
                # if stored_last_modified != head.headers.get("last-modified"):
                if (
                    head.headers.get("content-type")
                    in fileutils.FILE_CONTENT_TYPES.keys()
                ):
                    if handle_download_file(pd, ps, link, file_name):
                        download_count += 1
                    time.sleep(random.uniform(5.0, 10.0))
                else:
                    message: str = f"Found a weird content type {head.headers.get('content-type')} for file {file_name} at {pd.name}/{ps.name}."
                    logger.warning(message)
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(broadcaster.to_owner(message))
                # else:
                #     time.sleep(random.uniform(2.0, 4.0))
    return download_count


def handle_download_file(
    pd: PageData, ps: PageSection, link: str, file_name: str
) -> bool:
    rsp: requests.Response = requests.get(link)
    hash: str = hashlib.md5(rsp.content).hexdigest()

    entry: datautils.FileHistory = datautils.FileHistory(
        pd.name,
        ps.name,
        file_name,
        link,
        hash,
        rsp.headers.get("date"),
        rsp.headers.get("last-modified"),
    )

    did_download: bool = False

    if not datautils.file_entry_exists(entry):
        datautils.insert_file_history(entry)
        fileutils.write_file(
            rsp.content,
            file_name,
            pd.name,
            ps.name,
            datetime.strptime(entry.timestamp, datautils.DATE_FORMAT_HEADER),
        )
        did_download = True

    return did_download


def scout_pages(pages: list[PageData], broadcaster: broadcasts.Broadcaster) -> None:
    while True:
        changes: list[PageChangeBroadcast] = list()
        for pd in pages:
            for ps in pd.sections:
                ps.last_attempt = datetime.utcnow()
                change: PageChangeBroadcast = scout_change(pd, ps)
                if change:
                    changes.append(change)
                time.sleep(random.uniform(2.0, 10.0))
            time.sleep(random.uniform(2.0, 10.0))
        fileutils.write_pagedata(pages)
        if changes:
            message: str = f"Found changes!{os.linesep}{os.linesep.join([entry.to_str() for entry in changes])}"
            loop = asyncio.get_event_loop()
            loop.run_until_complete(broadcaster.to_owner(message))
        nap_time: int = random.uniform(1800.0, 3600.0)
        logger.info(f"Taking a nap for about {math.floor(nap_time/60)} minutes.")
        time.sleep(nap_time)


def process_changes(pages: list[PageData]) -> list[PageChangeBroadcast]:
    """
    Check and annotate where changes are.

    :pages - list to observe for changes
    """
    res: list[PageChangeBroadcast] = []
    for p in pages:
        for s in p.sections:
            if s.last_update > s.last_attempt:
                res.append(PageChangeBroadcast(p.name, s.name, s.last_update))
    return res


def request_content(url: str) -> requests.Response:
    """
    Attempt to get a certain resource, only accepting a 200.

    :url - resource to fetch
    """
    rsp: requests.Response = requests.get(url)

    if rsp.status_code != 200:
        logger.error(f"{url} returned {rsp.status_code}")
        raise requests.exceptions.RequestException

    return rsp


def generate_page_hash(soup: bs) -> str:
    """
    Generate hash of a given BeautifulSoup object.

    :soup - BeautifulSoup to hash
    """
    content = transform_response(soup)
    return hashlib.md5(content).hexdigest()


def transform_response(soup: bs) -> str:
    """
    Lazily encode the result of a BeautifulSoup object to Unicode.

    :soup - BeautifulSoup to encode
    """
    return soup.get_text().encode(encoding="UTF-8", errors="strict")


def on_change_detected(
    pd: PageData, ps: PageSection, rsp: requests.Response, hash: str
) -> None:
    """
    Update page state and save changes to file.

    :pd - page data where change was detected
    :ps - page section were change was detected
    :rsp - response where the change was observed
    :hash - calculated hash of the new content
    """
    try:
        ts = datetime.strptime(
            rsp.headers.get("last-modified") or rsp.headers.get("date"),
            datautils.DATE_FORMAT_HEADER,
        )
    except TypeError:
        ts = datetime.utcnow()
    ps.last_hash = hash
    ps.last_update = ts
    fileutils.write_page(pd.name, rsp.text, ts, ps.name)
    datautils.insert_page_history(
        datautils.PageHistory(
            pd.name,
            ps.name,
            ps.url,
            hash,
            rsp.headers.get("date"),
            rsp.headers.get("last-modified"),
        )
    )


def diff_page_data(pd: PageSection, hash: str) -> bool:
    """
    Silly small condition alias.

    :pd - PageSection that offers the last hash we want to compare
    :hash - just calculated page hash
    """
    return pd.last_hash != hash


def init_broadcaster() -> broadcasts.Broadcaster:
    """
    Create and register all used services for broadcast.
    """
    bot_instance: telegram.Bot = telegram.Bot(os.getenv("TELEGRAM_BOT_KEY"))
    owner_id: str = os.getenv("TELEGRAM_OWNER_ID")
    chat_ids: str = [owner_id]
    telegram_service: broadcasts.TelegramService = broadcasts.TelegramService(
        bot_instance, owner_id, chat_ids
    )

    broadcaster: broadcasts.Broadcaster = broadcasts.Broadcaster()
    broadcaster.register_telegram(telegram_service)

    return broadcaster


if __name__ == "__main__":
    load_dotenv(".env")

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    lf = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
    pathlib.Path("logs").mkdir(exist_ok=True)
    fh = logging.FileHandler("logs/app.log")
    fh.setLevel(logging.INFO)
    fh.setFormatter(lf)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(lf)
    logger.addHandler(fh)
    logger.addHandler(sh)

    logger.info("Starting program.")

    try:
        pages: list[PageData] = fileutils.read_pagedata()
        broadcaster: broadcasts.Broadcaster = init_broadcaster()
        datautils.setup_db()
        scout_pages(pages, broadcaster)
    except KeyboardInterrupt:
        msg: str = "Interruption signal caught."
        loop = asyncio.get_event_loop()
        loop.run_until_complete(broadcaster.to_owner(msg))
        logger.info(msg)
    except Exception:
        logger.exception("Unexpected exception occured.")
        loop = asyncio.get_event_loop()
        import traceback

        loop.run_until_complete(
            broadcaster.to_owner(
                f"Something went very wrong!{os.linesep}{os.linesep}{traceback.format_exc()}"
            )
        )

    logger.info("Stopping program.")
