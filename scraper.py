import concurrent.futures
import threading
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
IMAGE_ACCEPT = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"

MAX_IMAGES = 50
MAX_WORKERS = 8
PAGE_TIMEOUT = (5, 20)
IMAGE_TIMEOUT = (5, 15)
MAX_PAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024
CHUNK_SIZE = 64 * 1024

_IMAGE_ATTRS = ("src", "data-src", "data-original", "data-lazy-src",
                "data-url", "data-img")
_TEXT_TAGS = ("p", "blockquote", "li")


class ScrapeError(Exception):
    """A scrape failure with a user-readable message."""


_thread_local = threading.local()


def _session():
    """One requests.Session per calling thread, with retry/backoff."""
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        retry = Retry(
            total=2, backoff_factor=0.4,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}), raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _thread_local.session = session
    return session


def _read_limited(response, limit, what):
    """Read a streamed response body, refusing oversized payloads."""
    length = response.headers.get("Content-Length")
    if length and length.isdigit() and int(length) > limit:
        raise ScrapeError(
            f"{what} is larger than {limit // (1024 * 1024)} MB — skipped")
    buffer = bytearray()
    for chunk in response.iter_content(CHUNK_SIZE):
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise ScrapeError(
                f"{what} is larger than {limit // (1024 * 1024)} MB — skipped")
    return bytes(buffer)


def _srcset_first(srcset):
    first = srcset.split(",")[0].strip().split(" ")[0]
    return first if first else ""


class ScraperThread(QThread):
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)
    images_found = pyqtSignal(list, str)  # [(url, bytes)], summary text
    progress = pyqtSignal(int, int)       # completed, total

    def __init__(self, url, data_type):
        super().__init__()
        self.url = url
        self.data_type = data_type
        self.page_url = url
        self.base_url = url

    def download_image(self, img_url):
        if self.isInterruptionRequested():
            return None
        try:
            headers = dict(UA_HEADERS)
            headers["Accept"] = IMAGE_ACCEPT
            headers["Referer"] = self.page_url
            with _session().get(img_url, headers=headers,
                                timeout=IMAGE_TIMEOUT, stream=True) as resp:
                resp.raise_for_status()
                ctype = resp.headers.get("Content-Type", "")
                if ctype and not ctype.startswith("image/"):
                    return None
                return _read_limited(resp, MAX_IMAGE_BYTES, "Image")
        except (requests.RequestException, ScrapeError):
            return None

    def run(self):
        try:
            with _session().get(self.url, headers=UA_HEADERS,
                                timeout=PAGE_TIMEOUT, stream=True) as resp:
                resp.raise_for_status()
                ctype = (resp.headers.get("Content-Type")
                         or "").split(";")[0].strip().lower()
                if ctype and ctype not in ("text/html",
                                           "application/xhtml+xml") \
                        and not ctype.endswith("+xml"):
                    raise ScrapeError(
                        f"Server returned '{ctype}' — not a web page")
                self.page_url = resp.url
                body = _read_limited(resp, MAX_PAGE_BYTES, "Page")

            if self.isInterruptionRequested():
                return

            # Pass raw bytes so BeautifulSoup can sniff <meta charset>.
            soup = BeautifulSoup(body, "lxml")
            for tag in soup(["script", "style", "noscript", "template"]):
                tag.decompose()

            base_tag = soup.find("base", href=True)
            self.base_url = (urljoin(self.page_url, base_tag["href"].strip())
                             if base_tag else self.page_url)

            if self.data_type == "Headings":
                self._emit_headings(soup)
            elif self.data_type == "Links":
                self._emit_links(soup)
            elif self.data_type == "Text Content":
                self._emit_text(soup)
            elif self.data_type == "Images":
                self._emit_images(soup)
        except ScrapeError as e:
            self.error.emit(str(e))
        except requests.Timeout:
            self.error.emit(
                "Request timed out — the server is too slow or unreachable")
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            self.error.emit(f"Server returned HTTP {code}")
        except requests.SSLError:
            self.error.emit(
                "TLS certificate verification failed for this site")
        except requests.ConnectionError:
            self.error.emit(
                "Could not connect — check the URL and your connection")
        except requests.RequestException as e:
            self.error.emit(f"Request failed: {e.__class__.__name__}")
        except Exception as e:
            self.error.emit(f"Unexpected error: {e}")

    def _emit_headings(self, soup):
        lines = []
        for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            text = h.get_text(" ", strip=True)
            if text:
                level = int(h.name[1])
                lines.append(f"{'  ' * (level - 1)}[H{level}] {text}")
        if not lines:
            raise ScrapeError("No headings found on the page")
        self.result_ready.emit("\n".join(lines))

    def _emit_links(self, soup):
        lines = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            absolute = urljoin(self.base_url, href)
            if urlparse(absolute).scheme not in ("http", "https"):
                continue
            label = a.get_text(" ", strip=True)
            if not label:
                img = a.find("img")
                label = (img.get("alt", "") if img else "") or absolute
            if (label, absolute) in seen:
                continue
            seen.add((label, absolute))
            lines.append(f"{label} - {absolute}")
        if not lines:
            raise ScrapeError("No links found on the page")
        self.result_ready.emit("\n".join(lines))

    def _emit_text(self, soup):
        blocks = soup.find_all(_TEXT_TAGS)
        texts = []
        seen = set()
        for el in blocks:
            if any(parent.name in _TEXT_TAGS for parent in el.parents):
                continue
            text = " ".join(el.get_text(" ", strip=True).split())
            if text and text not in seen:
                seen.add(text)
                texts.append(text)
        if not texts:
            raise ScrapeError("No text content found on the page")
        self.result_ready.emit("\n\n".join(texts))

    def _collect_image_urls(self, soup):
        urls = []
        seen = set()

        def add(raw):
            if not raw:
                return
            absolute = urljoin(self.base_url, raw.strip())
            if urlparse(absolute).scheme not in ("http", "https"):
                return
            if absolute not in seen:
                seen.add(absolute)
                urls.append(absolute)

        for img in soup.find_all("img"):
            for attr in _IMAGE_ATTRS:
                add(img.get(attr))
            if img.get("srcset"):
                add(_srcset_first(img["srcset"]))
        for source in soup.find_all("source"):
            if source.get("srcset"):
                add(_srcset_first(source["srcset"]))
        return urls

    def _emit_images(self, soup):
        urls = self._collect_image_urls(soup)
        if not urls:
            raise ScrapeError("No images found on the page")

        capped = len(urls) > MAX_IMAGES
        if capped:
            urls = urls[:MAX_IMAGES]

        results = []
        done = 0
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)
        try:
            futures = {pool.submit(self.download_image, u): u for u in urls}
            for future in concurrent.futures.as_completed(futures):
                data = future.result()
                done += 1
                if data:
                    results.append((futures[future], data))
                self.progress.emit(done, len(urls))
                if self.isInterruptionRequested():
                    break
        finally:
            pool.shutdown(wait=not self.isInterruptionRequested(),
                          cancel_futures=True)

        if self.isInterruptionRequested():
            return

        failed = done - len(results)
        parts = [f"Found {len(results)} image"
                 + ("s" if len(results) != 1 else "")]
        if failed:
            parts.append(f"{failed} failed to download")
        if capped:
            parts.append(f"limited to the first {MAX_IMAGES}")
        listing = "\n".join(url for url, _ in results)
        summary = ", ".join(parts) + ("\n\n" + listing if listing else "")
        self.images_found.emit(results, summary)
