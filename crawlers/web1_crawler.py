# crawlers/web1_crawler.py
import aiohttp
import asyncio
from urllib.parse import urlparse, urljoin, ParseResult
from parsers.parser_html import WebPageProcessor
from utils.robots_checker import check_robots_txt_async
import logging
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

class Web1Crawler:
    def __init__(self, start_url: str, domain: str, max_pages: int = 1000, 
                 max_depth: int = 3, delay: float = 0.5, concurrency: int = 10,
                 output_file: str = "web_crawler_output.txt"):
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
        self.txt_file = output_file
        self._validate_initial_parameters()

    def _validate_initial_parameters(self):
        if not self.start_url.startswith(('http://', 'https://')):
            raise ValueError("Start URL должен начинаться с http:// или https://")
        if self.max_pages < 1:
            raise ValueError("Максимальное количество страниц должно быть >= 1")
        if self.max_depth < 0:
            raise ValueError("Максимальная глубина не может быть отрицательной")
        if self.delay < 0:
            raise ValueError("Задержка не может быть отрицательной")

    async def __aenter__(self):
        try:
            connector = aiohttp.TCPConnector(use_dns_cache=False)
            self.session = aiohttp.ClientSession(connector=connector)
            return self
        except Exception as e:
            logger.error(f"Ошибка инициализации сессии: {str(e)}")
            raise

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self.session:
                await self.session.close()
        except Exception as e:
            logger.error(f"Ошибка закрытия сессии: {str(e)}")

    async def check_robots_permission(self, url: str) -> bool:
        if not self.session:
            logger.error("Сессия не инициализирована")
            return False
        try:
            return await check_robots_txt_async(url, self.domain, self.session)
        except Exception as e:
            logger.warning(f"Ошибка проверки robots.txt для {url}: {str(e)}")
            return True  # По умолчанию разрешаем при ошибке проверки

    async def fetch_page(self, url: str) -> Optional[str]:
        if not self.session:
            logger.error("Сессия не инициализирована")
            return None
            
        try:
            async with self.semaphore:
                await asyncio.sleep(self.delay)
                
                # Проверка robots.txt
                if not await self.check_robots_permission(url):
                    logger.warning(f"Доступ запрещен robots.txt: {url}")
                    return None
                
                # Загрузка страницы
                async with self.session.get(url, timeout=10) as response:
                    response.raise_for_status()
                    content_type = response.headers.get('Content-Type', '')
                    
                    # Проверка типа контента
                    if 'text/html' not in content_type:
                        logger.info(f"Неподдерживаемый Content-Type: {content_type} для {url}")
                        return None
                        
                    return await response.text(errors='replace')  # Обработка ошибок декодирования

        except aiohttp.ClientError as e:
            logger.error(f"Клиентская ошибка при загрузке {url}: {str(e)}")
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при загрузке {url}")
        except Exception as e:
            logger.exception(f"Неизвестная ошибка при загрузке {url}: {str(e)}")
            
        self.stats["broken_pages"] += 1
        self.stats["error_links"].append(url)
        return None

    async def process_page(self, url: str, depth: int) -> List[Tuple[str, int]]:
        if depth > self.max_depth:
            return []
        
        html = await self.fetch_page(url)
        if not html:
            return []
        
        try:
            processor = WebPageProcessor(url, html)
        except Exception as e:
            logger.error(f"Ошибка парсинга {url}: {str(e)}")
            return []

        # Логирование первой строки текста
        try:
            first_line = processor.full_text.split("\n")[0] if processor.full_text else "Нет текста"
            logger.info(f"Первая строка текста на {url}: {first_line}")
        except Exception as e:
            logger.warning(f"Ошибка получения первой строки текста для {url}: {str(e)}")

        # Логирование первых ссылок
        try:
            first_links = [link["url"] for link in processor.links[:3]] if processor.links else []
            logger.info(f"Первые ссылки на {url}: {first_links}")
        except Exception as e:
            logger.warning(f"Ошибка обработки ссылок на {url}: {str(e)}")

        # Запись текста в файл
        if processor.full_text:
            try:
                self._write_to_txt(url, processor.full_text)
            except Exception as e:
                logger.error(f"Ошибка записи в файл для {url}: {str(e)}")

        # Обновление статистики
        try:
            self.stats["total_pages"] += 1
            self.stats["internal_pages"] += 1
        except Exception as e:
            logger.error(f"Ошибка обновления статистики для {url}: {str(e)}")

        new_links = []
        # Обработка ссылок
        try:
            for link_info in processor.links:
                full_url = self._normalize_url(link_info["url"])
                if not full_url:
                    continue
                    
                parsed = urlparse(full_url)
                
                try:
                    self.stats["total_links"] += 1
                except Exception as e:
                    logger.warning(f"Ошибка обновления счетчика ссылок для {url}: {str(e)}")

                # Обработка файлов
                if any(full_url.endswith(ext) for ext in ('.pdf', '.doc', '.docx')):
                    self._process_file_link(full_url)
                    continue

                # Обработка внутренних ссылок
                if self.domain in parsed.netloc:
                    self._process_internal_link(parsed, full_url, depth, new_links)
                else:
                    self._process_external_link(parsed.netloc)
        except Exception as e:
            logger.error(f"Критическая ошибка обработки ссылок на {url}: {str(e)}")

        return new_links

    def _normalize_url(self, url: str) -> Optional[str]:
        try:
            return urljoin(self.start_url, url)
        except Exception as e:
            logger.warning(f"Ошибка нормализации URL {url}: {str(e)}")
            return None

    def _write_to_txt(self, url: str, text: str):
        try:
            with open(self.txt_file, mode='a', encoding='utf-8', errors='replace') as file:
                file.write(f"URL: {url}\n")
                file.write("Text:\n")
                file.write(text[:100000])  # Ограничение длины записи
                file.write("\n" + "-" * 80 + "\n")
        except Exception as e:
            logger.error(f"Ошибка записи в файл {self.txt_file}: {str(e)}")
            raise

    def _process_file_link(self, url: str):
        try:
            ext = url.split('.')[-1].lower()
            if ext in ('pdf', 'doc', 'docx'):
                self.stats["files"][ext] += 1
                self.stats["files"]["total"] += 1
                self.stats["files"]["unique"].add(url)
        except Exception as e:
            logger.warning(f"Ошибка обработки файловой ссылки {url}: {str(e)}")

    def _process_internal_link(self, parsed: ParseResult, url: str, depth: int, new_links: list):
        try:
            if parsed.netloc not in self.stats["subdomains"]:
                self.stats["subdomains"].add(parsed.netloc)
            if depth < self.max_depth and url not in self.visited:
                new_links.append((url, depth+1))
        except Exception as e:
            logger.warning(f"Ошибка обработки внутренней ссылки {url}: {str(e)}")

    def _process_external_link(self, netloc: str):
        try:
            self.stats["external_links"]["total"] += 1
            self.stats["external_links"]["unique"].add(netloc)
        except Exception as e:
            logger.warning(f"Ошибка обработки внешней ссылки {netloc}: {str(e)}")

    async def worker(self):
        while True:
            try:
                url, depth = await self.queue.get()
                if url in self.visited or self.stats["total_pages"] >= self.max_pages:
                    self.queue.task_done()
                    continue

                self.visited.add(url)
                logger.info(f"Обработка {url} (глубина {depth})")
                
                new_links = await self.process_page(url, depth)
                
                # Добавление новых ссылок в очередь
                for link, new_depth in new_links:
                    try:
                        if link not in self.visited and self.stats["total_pages"] < self.max_pages:
                            await self.queue.put((link, new_depth))
                    except Exception as e:
                        logger.warning(f"Ошибка добавления ссылки {link} в очередь: {str(e)}")
                
                self.queue.task_done()
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Критическая ошибка в воркере: {str(e)}")
                self.queue.task_done()

    async def crawl(self) -> Dict[str, Any]:
        try:
            await self.queue.put((self.start_url, 0))
            tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]
            
            await self.queue.join()
            
            # Отмена задач после завершения
            for task in tasks:
                task.cancel()
            
            # Формирование итоговой статистики
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
        except Exception as e:
            logger.exception("Критическая ошибка в процессе краулинга")
            return {
                "error": str(e),
                **{k: v for k, v in self.stats.items()}
            }