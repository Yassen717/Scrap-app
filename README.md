# 🕷️ Modern Web Scraper

A fast, clean desktop web scraper built with Python and PyQt6.

## ✨ Features

- 🎨 Modern flat UI with five instant themes (Light, Dark, Nord,
  Solarized, Dracula) applied app-wide
- 🔍 Smart data extraction:
  - 📑 Headings (H1–H6, indented by level)
  - 🔗 Links resolved to absolute URLs (`text - url`)
  - 📝 Text content (paragraphs, quotes, list items)
  - 🖼️ Images — up to 50 downloaded in parallel and saved to a folder
    with safe, content-detected filenames
- ⚡ Background scraping — the UI stays responsive, with progress
  reporting and a Cancel button for slow pages
- 🛡️ Hardened fetching: size caps (20 MB), content-type checks,
  retries with backoff, per-thread connection reuse, and clear
  human-readable errors
- 💾 Remembers your last URL, content type, theme, and window geometry

## 🚀 Installation

1. Ensure you have **Python 3.10 or newer** installed
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (or `pip install .` — the project also ships a `pyproject.toml`)

## 🎮 Usage

```bash
python main.py
```

1. 🌐 Enter the target website URL (the `https://` prefix is added for you)
2. ✅ Choose a content type
3. 🚀 Press **Scrape Website** (or just hit Enter)

### ⌨️ Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Enter` | Scrape |
| `Ctrl+L` | Focus the URL field |
| `Ctrl+K` | Clear results |
| `Ctrl+Shift+C` | Copy all results |
| `Ctrl+S` | Save results to a file |
| `F1` | Help |

## ⚠️ Important note

Please ensure you have permission to scrape your target website and
comply with its Terms of Service, `robots.txt` rules, and rate limits.
The app sends a browser-like User-Agent, retries politely on 429/5xx,
and caps downloads at 50 images / 20 MB per response.

## 📜 License

This project's code is released under the MIT License (see `LICENSE`).
It depends on **PyQt6**, which is GPL-3.0/commercial — distributing
binaries built with it triggers GPL obligations (or requires a
commercial PyQt license).

---
<div align="center">
Made with ❤️ using Python and PyQt6
</div>
