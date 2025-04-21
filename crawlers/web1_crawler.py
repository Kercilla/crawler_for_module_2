# crawlers/web1_crawler.py
import aiohttp
import asyncio
from urllib.parse import urlparse, urljoin
from parsers.parser_html import WebPageProcessor
from utils.robots_checker import check_robots_txt_async
import logging

logger = logging.getLogger(__name__)

class Web1Crawler:
    def __init__(self, start_url, domain, max_pages=1000, max_depth=3, 
                 delay=0.5, concurrency=10):
        self.start_url = start_url
        self.domain = domain
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.delay = delay
        self.concurrency = concurrency
        self.queue = asyncio.Queue()
        self.visited = set()
        self.stats = {
            "total_pages": 0,
            "total_links": 0,
            "internal_pages": 0,
            "broken_pages": 0,
            "subdomains": set(),
            "external_links": {"total": 0, "unique": set()},
            "files": {"pdf": 0, "doc": 0, "docx": 0, "total": 0, "unique": set()},
            "error_links": []
        }
        self.session = None
        self.semaphore = asyncio.Semaphore(concurrency)
        self.txt_file = "web_crawler_output.txt"

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(use_dns_cache=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def check_robots_permission(self, url):
        return await check_robots_txt_async(url, self.domain, self.session)

    async def fetch_page(self, url):
        try:
            async with self.semaphore:
                await asyncio.sleep(self.delay)
                if not await self.check_robots_permission(url):
                    logger.warning(f"Доступ запрещен robots.txt: {url}")
                    return None
                async with self.session.get(url, timeout=10) as response:
                    response.raise_for_status()
                    return await response.text()
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url}: {str(e)}")
            self.stats["broken_pages"] += 1
            self.stats["error_links"].append(url)
            return None

    async def process_page(self, url, depth):
        html = await self.fetch_page(url)
        if not html:
            return []
        
        processor = WebPageProcessor(url, html)

        # Вывод первой строки спарсированного текста
        first_line = processor.full_text.split("\n")[0] if processor.full_text else "Нет текста"
        logger.info(f"Первая строка текста на {url}: {first_line}")

        # Вывод первых нескольких ссылок
        first_links = [link["url"] for link in processor.links[:3]] if processor.links else []
        logger.info(f"Первые ссылки на {url}: {first_links}")

        # Запись текста в TXT
        if processor.full_text:
            self._write_to_txt(url, processor.full_text)

        self.stats["total_pages"] += 1
        self.stats["internal_pages"] += 1
        
        new_links = []
        for link_info in processor.links:
            full_url = urljoin(self.start_url, link_info["url"])
            parsed = urlparse(full_url)
            
            self.stats["total_links"] += 1
            
            if full_url.endswith(('.pdf', '.doc', '.docx')):
                self._process_file_link(full_url)
                continue
            
            if self.domain in parsed.netloc:
                self._process_internal_link(parsed, full_url, depth, new_links)
            else:
                self._process_external_link(parsed.netloc)

        return new_links
    
    def _write_to_txt(self, url, text):
        """Записывает URL и текст в TXT-файл."""
        with open(self.txt_file, mode='a', encoding='utf-8') as file:
            file.write(f"URL: {url}\n")
            file.write("Text:\n")
            file.write(text)
            file.write("\n" + "-" * 80 + "\n")  # Разделитель между записями

    def _process_file_link(self, url):
        ext = url.split('.')[-1]
        if ext in ['pdf', 'doc', 'docx']:
            self.stats["files"][ext] += 1
            self.stats["files"]["total"] += 1
            self.stats["files"]["unique"].add(url)

    def _process_internal_link(self, parsed, url, depth, new_links):
        if parsed.netloc not in self.stats["subdomains"]:
            self.stats["subdomains"].add(parsed.netloc)
        if depth < self.max_depth and url not in self.visited:
            new_links.append((url, depth+1))

    def _process_external_link(self, netloc):
        self.stats["external_links"]["total"] += 1
        self.stats["external_links"]["unique"].add(netloc)

    async def worker(self):
        while True:
            url, depth = await self.queue.get()
            if url in self.visited or self.stats["total_pages"] >= self.max_pages:
                self.queue.task_done()
                continue
                
            self.visited.add(url)
            logger.info(f"Обработка {url} (глубина {depth})")
            new_links = await self.process_page(url, depth)
            
            for link, new_depth in new_links:
                if link not in self.visited and self.stats["total_pages"] < self.max_pages:
                    await self.queue.put((link, new_depth))
            
            self.queue.task_done()

    async def crawl(self):
        await self.queue.put((self.start_url, 0))
        tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]
        
        await self.queue.join()
        
        for task in tasks:
            task.cancel()
        
        return {
            "total_pages": self.stats["total_pages"],
            "total_links": self.stats["total_links"],
            "internal_pages": self.stats["internal_pages"],
            "broken_pages": self.stats["broken_pages"],
            "subdomains": list(self.stats["subdomains"]),
            "external_links": {
                "total": self.stats["external_links"]["total"],
                "unique": list(self.stats["external_links"]["unique"])
            },
            "files": {
                "total": self.stats["files"]["total"],
                "pdf": self.stats["files"]["pdf"],
                "doc": self.stats["files"]["doc"],
                "docx": self.stats["files"]["docx"],
                "unique": list(self.stats["files"]["unique"])
            },
            "error_links": self.stats["error_links"]
        }