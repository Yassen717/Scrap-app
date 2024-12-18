from PyQt6.QtCore import QThread, pyqtSignal
import requests
from bs4 import BeautifulSoup

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
            response = requests.get(img_url)
            response.raise_for_status()
            return response.content
        except:
            return None

    def run(self):
        try:
            response = requests.get(self.url)
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
                result = "\n".join([f"{link.text.strip()} - {link['href']}" 
                                  for link in links if link.text.strip()])
            elif self.data_type == "Text Content":
                paragraphs = soup.find_all('p')
                result = "\n\n".join([p.text.strip() for p in paragraphs])
            elif self.data_type == "Images":
                images = soup.find_all('img', src=True)
                image_data_list = []
                
                for img in images:
                    img_url = img['src']
                    if not img_url.startswith(('http://', 'https://')):
                        # Handle relative URLs
                        if img_url.startswith('/'):
                            base_url = '/'.join(self.url.split('/')[:3])
                            img_url = base_url + img_url
                        else:
                            img_url = self.url.rstrip('/') + '/' + img_url
                    
                    img_data = self.download_image(img_url)
                    if img_data:
                        image_data_list.append((img_url, img_data))
                
                if image_data_list:
                    self.images_found.emit(image_data_list)
                result = f"Found {len(image_data_list)} images"
            
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
