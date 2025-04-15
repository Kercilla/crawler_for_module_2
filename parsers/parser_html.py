# parsers/parser_html.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class WebPageProcessor:
    def __init__(self, url, html_content):
        self.url = url
        self.soup = self._parse_content(html_content)
        self.full_text = ""
        self.images = []
        self.tables = []
        self.meta_tags = {}
        self.links = []
        if self.soup:
            self.full_text = self._extract_full_text()
            self.images = self._extract_images()
            self.tables = self._extract_tables()
            self.meta_tags = self._extract_meta_tags()
            self.links = self._extract_links()

    def _parse_content(self, content):
        try:
            return BeautifulSoup(content, 'html.parser')
        except Exception as e:
            logger.error(f"Ошибка парсинга {self.url}: {str(e)}")
            return None

    def _extract_full_text(self):
        try:
            raw_text = self.soup.get_text(separator="\n", strip=True)
            # Очищаем текст от лишних символов
            clean_text = self._clean_text(raw_text)
            return clean_text
        except Exception as e:
            logger.warning(f"Ошибка извлечения текста из {self.url}: {str(e)}")
            return ""

    def _clean_text(self, text):
        # Удаляем \xa0 и лишние пробелы
        text = text.replace("\xa0", " ")
        #text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_images(self):
        images = []
        for img in self.soup.find_all("img"):
            src = urljoin(self.url, img.get("src", ""))
            images.append({
                "src": src,
                "alt": img.get("alt", "No alt text")
            })
        return images

    def _extract_tables(self):
        tables = []
        for table in self.soup.find_all("table"):
            headers = [th.text.strip() for th in table.find_all("th")]
            rows = [[td.text.strip() for td in row.find_all("td")] 
                    for row in table.find_all("tr")]
            tables.append({"headers": headers, "rows": rows})
        return tables

    def _extract_meta_tags(self):
        meta_tags = {}
        for meta in self.soup.find_all("meta"):
            name = meta.get("name") or meta.get("property") or meta.get("http-equiv")
            content = meta.get("content")
            if name and content:
                meta_tags[name.lower()] = content
        return meta_tags

    def _extract_links(self):
        links = []
        for a in self.soup.find_all("a", href=True):
            full_url = urljoin(self.url, a["href"])
            links.append({
                "text": a.text.strip(),
                "url": full_url
            })
        return links