"""Self-contained smoke test: serves a fixture site locally and drives the
scraper + app widgets offscreen. Run: ``python smoke_test.py``."""
import binascii
import functools
import http.server
import os
import struct
import sys
import threading
import zlib

os.environ.setdefault("QT_QPA_PLATFORM", "minimal")

from PyQt6.QtCore import QEventLoop, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

SITE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "_test_site")


def _png_bytes():
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", binascii.crc32(tag + data)))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    return (sig + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\xff"))
            + chunk(b"IEND", b""))


def _build_site(base_url):
    os.makedirs(os.path.join(SITE_ROOT, "sub"), exist_ok=True)
    html = f"""<!DOCTYPE html>
<html><head><title>Test Page</title>
<base href="{base_url}/sub/"><meta charset="utf-8">
</head><body>
<h1>Main <b>Title</b></h1><h2>Sub Heading</h2><h6>Deep</h6>
<p>Hello <i>world</i></p>
<p>Second para<script>track()</script></p>
<ul><li>item one</li><li>item two</li></ul>
<a href="/about">About</a>
<a href="javascript:void(0)">bad link</a>
<a href="">empty href</a>
<a href="page2.html?q=1"><img src="x.png" alt="img link"></a>
<img src="/pic.png"><img data-src="lazy.jpg"><img src="">
<img srcset="/srcset.webp 1x, /srcset2.webp 2x">
</body></html>"""
    with open(os.path.join(SITE_ROOT, "index.html"), "w",
              encoding="utf-8") as f:
        f.write(html)
    for folder in (SITE_ROOT, os.path.join(SITE_ROOT, "sub")):
        for name in ("pic.png", "srcset.webp", "x.png"):
            with open(os.path.join(folder, name), "wb") as f:
                f.write(_png_bytes())
        with open(os.path.join(folder, "lazy.jpg"), "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 16 + b"\xff\xd9")


def _start_server():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=SITE_ROOT)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    _build_site(f"http://127.0.0.1:{port}")
    return httpd, port


def run_scrape(url, data_type):
    """Drive a ScraperThread to completion on the current event loop."""
    from scraper import ScraperThread
    out = {"result": None, "error": None, "images": None, "progress": []}
    loop = QEventLoop()
    t = ScraperThread(url, data_type)
    t.result_ready.connect(lambda s: out.__setitem__("result", s))
    t.error.connect(lambda s: out.__setitem__("error", s))
    t.images_found.connect(
        lambda lst, s: out.__setitem__("images", (lst, s)))
    t.progress.connect(lambda d, tot: out["progress"].append((d, tot)))
    t.finished.connect(loop.quit)
    t.start()
    QTimer.singleShot(30000, loop.quit)
    loop.exec()
    return out


def main():
    httpd, port = _start_server()
    base = f"http://127.0.0.1:{port}"
    print(f"fixture server on :{port}")

    app = QApplication(sys.argv)  # noqa: F841  (must stay referenced)

    r = run_scrape(f"{base}/index.html", "Headings")
    assert r["result"] and "[H1] Main Title" in r["result"], r
    assert "track()" not in r["result"], "script leaked into headings"
    print("headings OK")

    r = run_scrape(f"{base}/index.html", "Links")
    assert r["result"], r
    assert f"{base}/about" in r["result"], "absolute link not resolved"
    assert f"{base}/sub/page2.html" in r["result"], "base href not honored"
    assert "javascript:" not in r["result"], "javascript link leaked"
    assert "img link" in r["result"], "img-alt label fallback failed"
    print("links OK")

    r = run_scrape(f"{base}/index.html", "Text Content")
    assert r["result"], r
    assert "Hello world" in r["result"], "glued text"
    assert "track()" not in r["result"], "script leaked"
    assert "item one" in r["result"], "li missing"
    print("text OK")

    r = run_scrape(f"{base}/index.html", "Images")
    assert r["images"], r
    urls = [u for u, _ in r["images"][0]]
    assert f"{base}/pic.png" in urls
    assert f"{base}/sub/lazy.jpg" in urls, "data-src missed"
    assert not any(u.endswith("/index.html") for u in urls), \
        "empty src fetched page"
    assert r["progress"], "no progress signals"
    print("images OK")

    r = run_scrape(f"{base}/missing.html", "Headings")
    assert r["error"] and "HTTP 404" in r["error"], r
    print("404 handling OK")

    from app import WebScraperApp, _safe_image_name
    w = WebScraperApp()
    w.show()
    for name in ("Light", "Dark", "Nord", "Solarized", "Dracula"):
        w.apply_theme(name)
    print("themes OK")

    cases = {
        "": None, "exa mple.com": None, "https://[": None,
        "ftp://x.com": None, "file:///c:/x": None,
        "HTTP://x.com": "http://x.com",
        "https://user:pw@host.com/a": "https://host.com/a",
        "  spaced.com  ": "https://spaced.com",
    }
    for raw, expected in cases.items():
        w.url_input.setText(raw)
        assert w._validated_url() == expected, (raw, expected)
    print("url validation OK")

    assert _safe_image_name("http://x/a.jpg:stream", b"\xff\xd8\xff", 1) \
        == "a.jpg"
    assert _safe_image_name("http://x/NUL", b"\x89PNG\r\n\x1a\n" * 3, 2) \
        == "image_2.png"
    assert _safe_image_name("http://x/e\u202egpj.exe", b"\xff\xd8\xff", 3) \
        == "e_gpj.jpg"
    print("filename sanitizer OK")

    w.url_input.setText(f"{base}/index.html")
    w.start_scraping()
    w.close()  # must not crash on a running scrape
    print("close mid-scrape OK")

    httpd.shutdown()
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
