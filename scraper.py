from PyQt6.QtCore import QThread, pyqtSignal
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import concurrent.futures

UA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) WebScraper/1.0'
}

MAX_IMAGES = 50
MAX_WORKERS = 8

class ScraperThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    images_found = pyqtSignal(list)  # Changed to emit list of tuples (url, data)

    def __init__(self, url, data_type):
        super().__init__()
        self.url = url
        self.data_type = data_type

    def download_image(self, img_url):
        try:
            response = requests.get(img_url, headers=UA_HEADERS, timeout=(5, 15))
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            return None

    def run(self):
        try:
            response = requests.get(self.url, headers=UA_HEADERS, timeout=(5, 10))
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            
            result = ""
            if self.data_type == "Headings":
                headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if not headings:
                    self.error.emit("No headings found on the page")
                    return
                
                heading_texts = []
                for h in headings:
                    level = int(h.name[1])  # Get heading level (1-6)
                    indent = "  " * (level - 1)  # Indent based on heading level
                    text = h.text.strip()
                    if text:  # Only include non-empty headings
                        heading_texts.append(f"{indent}[H{level}] {text}")
                
                if heading_texts:
                    result = "\n".join(heading_texts)
                else:
                    self.error.emit("No non-empty headings found on the page")
                    return
            elif self.data_type == "Links":
                links = soup.find_all('a', href=True)
                entries = [f"{link.text.strip()} - {link['href']}" for link in links if link.text.strip()]
                if not entries:
                    self.error.emit("No links with non-empty text found on the page")
                    return
                result = "\n".join(entries)
            elif self.data_type == "Text Content":
                paragraphs = soup.find_all('p')
                texts = [p.text.strip() for p in paragraphs if p.text.strip()]
                if not texts:
                    self.error.emit("No non-empty paragraph text found on the page")
                    return
                result = "\n\n".join(texts)
            elif self.data_type == "Images":
                images = soup.find_all('img', src=True)
                # Build list of absolute URLs, keep order and unique entries
                urls = []
                seen = set()
                for img in images:
                    u = urljoin(self.url, img.get('src', ''))
                    if not u:
                        continue
                    if u in seen:
                        continue
                    seen.add(u)
                    urls.append(u)
                
                # Apply cap to avoid huge downloads
                capped = False
                if len(urls) > MAX_IMAGES:
                    urls = urls[:MAX_IMAGES]
                    capped = True
                
                image_data_list = []
                if urls:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        for img_url, img_data in zip(urls, executor.map(self.download_image, urls)):
                            if img_data:
                                image_data_list.append((img_url, img_data))
                
                if image_data_list:
                    self.images_found.emit(image_data_list)
                cap_note = " (limited to first %d)" % MAX_IMAGES if capped else ""
                result = f"Found {len(image_data_list)} images{cap_note}"
            
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
