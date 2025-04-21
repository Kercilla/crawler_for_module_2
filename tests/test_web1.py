import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from crawlers.web1_crawler import Web1Crawler
from urllib.parse import urlparse


class TestWeb1Crawler(unittest.TestCase):
    def setUp(self):
        self.start_url = "http://spbu.ru"
        self.domain = "spbu.ru"
        self.max_pages = 10
        self.max_depth = 2
        self.delay = 0.1
        self.concurrency = 3

    async def asyncSetUp(self):
        self.crawler = Web1Crawler(
            start_url=self.start_url,
            domain=self.domain,
            max_pages=self.max_pages,
            max_depth=self.max_depth,
            delay=self.delay,
            concurrency=self.concurrency
        )
        self.crawler.session = AsyncMock()  # Мок сессии

    async def asyncTearDown(self):
        if hasattr(self, 'crawler') and self.crawler.session:
            await self.crawler.session.close()

    async def test_initialization(self):
        """Тест инициализации краулера"""
        self.assertEqual(self.crawler.start_url, self.start_url)
        self.assertEqual(self.crawler.domain, self.domain)
        self.assertEqual(self.crawler.max_pages, self.max_pages)
        self.assertEqual(self.crawler.max_depth, self.max_depth)
        self.assertEqual(self.crawler.delay, self.delay)
        self.assertEqual(self.crawler.concurrency, self.concurrency)
        self.assertEqual(self.crawler.stats["total_pages"], 0)

    @patch('crawlers.web1_crawler.check_robots_txt_async')
    async def test_check_robots_permission(self, mock_check_robots):
        """Тест проверки разрешения в robots.txt"""
        mock_check_robots.return_value = True
        result = await self.crawler.check_robots_permission(self.start_url)
        self.assertTrue(result)
        mock_check_robots.assert_called_once_with(self.start_url, self.domain, self.crawler.session)

    @patch('crawlers.web1_crawler.check_robots_txt_async')
    async def test_fetch_page_success(self, mock_check_robots):
        """Тест успешной загрузки страницы"""
        mock_check_robots.return_value = True
        mock_response = AsyncMock()
        mock_response.text.return_value = "<html>Test</html>"
        mock_response.raise_for_status.return_value = None
        self.crawler.session.get.return_value.__aenter__.return_value = mock_response

        result = await self.crawler.fetch_page(self.start_url)
        self.assertEqual(result, "<html>Test</html>")

    @patch('crawlers.web1_crawler.check_robots_txt_async')
    async def test_fetch_page_robots_denied(self, mock_check_robots):
        """Тест отклонения доступа robots.txt"""
        mock_check_robots.return_value = False
        result = await self.crawler.fetch_page(self.start_url)
        self.assertIsNone(result)

    @patch('crawlers.web1_crawler.check_robots_txt_async')
    async def test_fetch_page_error(self, mock_check_robots):
        """Тест ошибки при загрузке страницы"""
        mock_check_robots.return_value = True
        self.crawler.session.get.side_effect = Exception("Test error")
        result = await self.crawler.fetch_page(self.start_url)
        self.assertIsNone(result)
        self.assertEqual(self.crawler.stats["broken_pages"], 1)

    @patch('crawlers.web1_crawler.WebPageProcessor')
    @patch('crawlers.web1_crawler.check_robots_txt_async')
    async def test_process_page(self, mock_check_robots, mock_processor):
        """Тест обработки страницы"""
        mock_check_robots.return_value = True
        mock_response = AsyncMock()
        mock_response.text.return_value = "<html>Test</html>"
        self.crawler.session.get.return_value.__aenter__.return_value = mock_response

        # Настройка мока процессора
        mock_processor_instance = MagicMock()
        mock_processor_instance.full_text = "Sample text\nSecond line"
        mock_processor_instance.links = [
            {"url": "/page1"},
            {"url": "/page2"},
            {"url": "http://external.com"},
            {"url": "file.pdf"}
        ]
        mock_processor.return_value = mock_processor_instance

        new_links = await self.crawler.process_page(self.start_url, 0)

        # Проверки
        self.assertEqual(len(new_links), 2)  # Только внутренние ссылки в пределах глубины
        self.assertEqual(self.crawler.stats["total_pages"], 1)
        self.assertEqual(self.crawler.stats["internal_pages"], 1)
        self.assertEqual(self.crawler.stats["total_links"], 4)
        self.assertEqual(self.crawler.stats["files"]["pdf"], 1)
        self.assertEqual(self.crawler.stats["external_links"]["total"], 1)

    async def test_process_internal_link(self):
        """Тест обработки внутренней ссылки"""
        test_url = "https://spbu.ru/education"
        parsed = urlparse(test_url)
        new_links = []

        self.crawler._process_internal_link(parsed, test_url, 0, new_links)

        self.assertEqual(len(new_links), 1)
        self.assertEqual(new_links[0], (test_url, 1))
        self.assertEqual(len(self.crawler.stats["subdomains"]), 1)

    async def test_process_external_link(self):
        """Тест обработки внешней ссылки"""
        test_domain = "https://google.com"
        self.crawler._process_external_link(test_domain)

        self.assertEqual(self.crawler.stats["external_links"]["total"], 1)
        self.assertEqual(len(self.crawler.stats["external_links"]["unique"]), 1)
        self.assertIn(test_domain, self.crawler.stats["external_links"]["unique"])

    async def test_process_file_link(self):
        """Тест обработки ссылки на файл"""
        test_urls = [
            "https://spbu.ru/sites/default/files/2025-04/20250428_povestka_sop_criminal.pdf",
        ]

        for url in test_urls:
            self.crawler._process_file_link(url)

        self.assertEqual(self.crawler.stats["files"]["pdf"], 1),
        self.assertEqual(self.crawler.stats["files"]["total"], 3)
        self.assertEqual(len(self.crawler.stats["files"]["unique"]), 3)

    @patch('crawlers.web1_crawler.Web1Crawler.process_page')
    async def test_worker(self, mock_process_page):
        """Тест работы воркера"""
        mock_process_page.return_value = []
        self.crawler.queue = asyncio.Queue()
        await self.crawler.queue.put((self.start_url, 0))

        worker_task = asyncio.create_task(self.crawler.worker())
        await asyncio.sleep(0.1)  # Даем время воркеру обработать задачу

        self.assertTrue(self.start_url in self.crawler.visited)
        mock_process_page.assert_called_once_with(self.start_url, 0)

        worker_task.cancel()  # Останавливаем воркер

    @patch('crawlers.web1_crawler.Web1Crawler.worker')
    async def test_crawl(self, mock_worker):
        """Тест основного метода crawl"""
        self.crawler.queue = asyncio.Queue()
        mock_worker.return_value = None

        result = await self.crawler.crawl()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["total_pages"], 0)  # В моке process_page не вызывается

        expected_keys = [
            "total_pages", "total_links", "internal_pages", "broken_pages",
            "subdomains", "external_links", "files", "error_links"
        ]
        for key in expected_keys:
            self.assertIn(key, result)

    @patch('builtins.open')
    async def test_write_to_txt(self, mock_open):
        """Тест записи в TXT файл"""
        test_url = "http://spbu.ru"
        test_text = "Sample text\nWith multiple lines"

        file_mock = MagicMock()
        mock_open.return_value.__enter__.return_value = file_mock

        self.crawler._write_to_txt(test_url, test_text)

        mock_open.assert_called_once_with(self.crawler.txt_file, mode='a', encoding='utf-8')
        file_mock.write.assert_any_call(f"URL: {test_url}\n")
        file_mock.write.assert_any_call("Text:\n")
        file_mock.write.assert_any_call(test_text)
        file_mock.write.assert_any_call("\n" + "-" * 80 + "\n")


if __name__ == '__main__':
    unittest.main()