import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from collections import deque
from parsers.parser_html import WebPageProcessor 
from config import DOMAINS_WEB1, ROBOTS_TXT_CHECK

class Web1Crawler:
    def __init__(self, start_url, domain):
        self.start_url = start_url
        self.domain = domain
        self.visited = set()
        self.queue = deque([start_url])
        self.stats = {
            "total_pages": 0,
            "internal_pages": 0,
            "broken_pages": 0,
            "subdomains": set(),
            "external_links": set(),
            "files": {"pdf": 0, "doc": 0, "docx": 0},
            "file_links": set()
        }

    def is_internal(self, url):
        return self.domain in url

    def check_robots_txt(self, url):
        # Проверка robots.txt (упрощенная)
        robots_url = urljoin(url, "/robots.txt")
        try:
            response = requests.get(robots_url, timeout=5)
            return "Disallow:" not in response.text
        except:
            return True  # Если robots.txt недоступен, считаем доступ разрешенным

    def parse_page(self, url):
        if ROBOTS_TXT_CHECK and not self.check_robots_txt(url):
            return None

        try:
            response = requests.get(url, timeout=10)
            if response.status_code >= 400:
                self.stats["broken_pages"] += 1
                return None
        except:
            self.stats["broken_pages"] += 1
            return None

        # Используем ваш HTML-парсер для извлечения текста
        parsed_content = WebPageProcessor(response.text)
        return parsed_content, response.text

    def extract_links(self, soup, current_url):
        links = []
        for a_tag in soup.find_all('a', href=True):
            full_url = urljoin(current_url, a_tag['href'])
            parsed = urlparse(full_url)
            
            # Обработка файлов
            if full_url.endswith('.pdf'):
                self.stats["files"]["pdf"] += 1
                self.stats["file_links"].add(full_url)
            elif full_url.endswith('.docx'):
                self.stats["files"]["docx"] += 1
                self.stats["file_links"].add(full_url)
            elif full_url.endswith('.doc'):
                self.stats["files"]["doc"] += 1
                self.stats["file_links"].add(full_url)
            
            # Обработка поддоменов и внешних ссылок
            if parsed.netloc.endswith(self.domain):
                links.append(full_url)
                self.stats["subdomains"].add(parsed.netloc)
            else:
                self.stats["external_links"].add(parsed.netloc)
        return links

    def crawl(self):
        while self.queue:
            url = self.queue.popleft()
            if url in self.visited:
                continue
            self.visited.add(url)
            
            # Парсинг страницы
            result = self.parse_page(url)
            if not result:
                continue
            parsed_content, raw_html = result
            
            # Обновление статистики
            self.stats["total_pages"] += 1
            self.stats["internal_pages"] += 1
            
            # Извлечение ссылок
            soup = BeautifulSoup(raw_html, 'lxml')
            new_links = self.extract_links(soup, url)
            for link in new_links:
                if link not in self.visited and link not in self.queue:
                    self.queue.append(link)
        
        # Конвертация множеств в списки
        self.stats["subdomains"] = list(self.stats["subdomains"])
        self.stats["external_links"] = list(self.stats["external_links"])
        self.stats["file_links"] = list(self.stats["file_links"])
        return self.stats
