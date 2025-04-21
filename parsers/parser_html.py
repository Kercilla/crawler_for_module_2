# parsers/parser_html.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import re

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
            try:
                self.full_text = self._extract_full_text()
                self.images = self._extract_images()
                self.tables = self._extract_tables()
                self.meta_tags = self._extract_meta_tags()
                self.links = self._extract_links()
            except Exception as e:
                logger.error(f"Критическая ошибка при обработке {url}: {str(e)}")
                # В случае критических ошибок сбрасываем все данные
                self.full_text = ""
                self.images = []
                self.tables = []
                self.meta_tags = {}
                self.links = []

    def _parse_content(self, content):
        if not content:
            logger.warning(f"Пустой контент для парсинга: {self.url}")
            return None
            
        try:
            return BeautifulSoup(content, 'html.parser')
        except Exception as e:
            logger.error(f"Ошибка парсинга {self.url}: {str(e)}")
            return None

    def _extract_full_text(self):
        if not self.soup:
            return ""
            
        try:
            raw_text = self.soup.get_text(separator="\n", strip=True)
            clean_text = self._clean_text(raw_text)
            return clean_text
        except Exception as e:
            logger.warning(f"Ошибка извлечения текста из {self.url}: {str(e)}")
            return ""

    def _clean_text(self, text):
        try:
            text = text.replace("\xa0", " ")
            text = re.sub(r"\s+", " ", text).strip()
            return text
        except Exception as e:
            logger.warning(f"Ошибка очистки текста из {self.url}: {str(e)}")
            return text  # Возвращаем оригинальный текст если очистка не удалась

    def _extract_images(self):
        if not self.soup:
            return []
            
        try:
            images = []
            for img in self.soup.find_all("img"):
                src = urljoin(self.url, img.get("src", ""))
                alt = img.get("alt", "No alt text")[:1000]  # Ограничение длины
                images.append({"src": src, "alt": alt})
            return images
        except Exception as e:
            logger.error(f"Ошибка извлечения изображений из {self.url}: {str(e)}")
            return []

    def _extract_tables(self):
        if not self.soup:
            return []
            
        try:
            tables = []
            for table in self.soup.find_all("table"):
                headers = [th.text.strip()[:500] for th in table.find_all("th")]
                rows = []
                for row in table.find_all("tr"):
                    cells = [td.text.strip()[:500] for td in row.find_all("td")]
                    if cells:  # Пропускаем пустые строки
                        rows.append(cells)
                if headers or rows:  # Добавляем только непустые таблицы
                    tables.append({"headers": headers, "rows": rows})
            return tables
        except Exception as e:
            logger.error(f"Ошибка извлечения таблиц из {self.url}: {str(e)}")
            return []

    def _extract_meta_tags(self):
        if not self.soup:
            return {}
            
        try:
            meta_tags = {}
            for meta in self.soup.find_all("meta"):
                name = (meta.get("name") or meta.get("property") or 
                        meta.get("http-equiv") or "unknown")
                content = meta.get("content", "No content")
                meta_tags[name.lower()[:200]] = content[:1000]  # Ограничение длины
            return meta_tags
        except Exception as e:
            logger.error(f"Ошибка извлечения метатегов из {self.url}: {str(e)}")
            return {}

    def _extract_links(self):
        if not self.soup:
            return []
            
        try:
            links = []
            for a in self.soup.find_all("a", href=True):
                full_url = urljoin(self.url, a["href"])
                link_text = a.text.strip()[:500]  # Ограничение длины текста
                if full_url:  # Пропускаем пустые URL
                    links.append({"text": link_text, "url": full_url})
            return links
        except Exception as e:
            logger.error(f"Ошибка извлечения ссылок из {self.url}: {str(e)}")
            return []