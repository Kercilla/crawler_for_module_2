import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import pandas as pd
from crawlers.web2_telegram_crawler import TelegramCrawler


class TestTelegramCrawler(unittest.TestCase):
    def setUp(self):
        self.max_messages = 100
        self.delay = 0.1

    async def asyncSetUp(self):
        self.crawler = TelegramCrawler(max_messages=self.max_messages, delay=self.delay)
        self.crawler.auth_manager = MagicMock()
        self.crawler.client = AsyncMock()

        self.mock_message = MagicMock()
        self.mock_message.message = "Test message"
        self.mock_message.views = 100
        self.mock_message.forwards = 10
        self.mock_message.date = datetime.now(timezone.utc)
        self.mock_message.replies = MagicMock()
        self.mock_message.replies.replies = 5

        self.mock_dialog = MagicMock()
        self.mock_dialog.id = 123
        self.mock_dialog.name = "Центр карьер СПбГУ"

    async def asyncTearDown(self):
        if hasattr(self, 'crawler') and hasattr(self.crawler, 'client'):
            await self.crawler.auth_manager.disconnect()

    async def test_initialization(self):
        """Тест инициализации краулера"""
        self.assertEqual(self.crawler.max_messages, self.max_messages)
        self.assertEqual(self.crawler.delay, self.delay)
        self.assertIsInstance(self.crawler.stats, dict)
        self.assertEqual(len(self.crawler.stats["channels"]), 0)

    async def test_start(self):
        """Тест подключения к Telegram API"""
        self.crawler.auth_manager.start = AsyncMock(return_value="mock_client")
        await self.crawler.start()
        self.assertEqual(self.crawler.client, "mock_client")
        self.crawler.auth_manager.start.assert_called_once()

    @patch('web2_telegram_crawler.logger')
    async def test_find_channels_success(self, mock_logger):
        """Тест поиска каналов"""
        # Настройка моков
        mock_dialog1 = MagicMock()
        mock_dialog1.name = "МГУ Official Channel"
        mock_dialog2 = MagicMock()
        mock_dialog2.name = "СПбГУ"

        self.crawler.client.iter_dialogs = AsyncMock()
        self.crawler.client.iter_dialogs.return_value = [mock_dialog1, mock_dialog2]
        self.crawler.search_messages = AsyncMock()

        await self.crawler.find_channels()

        self.crawler.client.iter_dialogs.assert_called_once()
        self.assertEqual(self.crawler.search_messages.call_count, 2)
        mock_logger.info.assert_any_call("Поиск каналов для МГУ")
        mock_logger.info.assert_any_call("Поиск каналов для СПбГУ")

    async def test_search_messages_success(self):
        """Тест поиска сообщений в канале"""
        mock_result = MagicMock()
        mock_result.messages = [self.mock_message] * 3
        self.crawler.client.return_value = mock_result
        self.crawler.process_message = AsyncMock()

        await self.crawler.search_messages(self.mock_dialog, "Test Channel", "МГУ")

        # Проверки
        self.crawler.client.assert_called_once()
        self.assertEqual(self.crawler.process_message.call_count, 3)

    async def test_search_messages_flood_wait(self):
        """Тест обработки FloodWaitError"""
        self.crawler.client.side_effect = FloodWaitError(seconds=10)
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await self.crawler.search_messages(self.mock_dialog, "Test Channel", "МГУ")
            mock_sleep.assert_called_once_with(10)

    async def test_process_message(self):
        """Тест обработки сообщения"""
        await self.crawler.process_message(self.mock_message, "Test Channel", "МГУ")

        stats = self.crawler.stats
        self.assertEqual(stats["university"][-1], "МГУ")
        self.assertEqual(stats["channels"][-1], "Test Channel")
        self.assertEqual(stats["messages"][-1], "Test message")
        self.assertEqual(stats["views"][-1], 100)
        self.assertEqual(stats["forwards"][-1], 10)
        self.assertEqual(stats["comments"][-1], 5)
        self.assertIsInstance(stats["date"][-1], datetime)

    @patch('pandas.DataFrame.to_csv')
    async def test_save_to_csv(self, mock_to_csv):
        """Тест сохранения в CSV"""
        self.crawler.stats = {
            "university": ["МГУ", "СПбГУ"],
            "channels": ["Студенческий совет СПбГУ", "Центр карьер СПбГУ"],
            "messages": ["Msg 1", "Msg 2"],
            "views": [100, 200],
            "comments": [5, 10],
            "forwards": [2, 4],
            "date": [datetime.now(), datetime.now()]
        }

        self.crawler.save_to_csv()

        mock_to_csv.assert_called_once_with('Telegram_posts.csv', index=False, encoding='utf-8')
        self.assertIsInstance(self.crawler.df, pd.DataFrame)
        self.assertEqual(len(self.crawler.df), 2)

    @patch('matplotlib.pyplot.figure')
    @patch('matplotlib.pyplot.savefig')
    async def test_generate_plot(self, mock_savefig, mock_figure):
        """Тест генерации графика"""
        # Создаем тестовый DataFrame
        test_data = {
            "university": ["МГУ"] * 3 + ["СПбГУ"] * 2,
            "date": pd.to_datetime([
                "2023-01-01", "2023-01-01", "2023-01-02",
                "2023-01-01", "2023-01-03"
            ])
        }
        self.crawler.df = pd.DataFrame(test_data)

        self.crawler.generate_plot()

        mock_savefig.assert_called_once_with('daily_posts.png', dpi=300, bbox_inches='tight')
        mock_figure.assert_called_once_with(figsize=(16, 10))

    @patch('web2_telegram_crawler.TelegramCrawler.start')
    @patch('web2_telegram_crawler.TelegramCrawler.find_channels')
    @patch('web2_telegram_crawler.TelegramCrawler.save_to_csv')
    @patch('web2_telegram_crawler.TelegramCrawler.generate_plot')
    async def test_crawl(self, mock_plot, mock_csv, mock_find, mock_start):
        """Тест основного метода crawl"""
        # Настраиваем моки
        mock_start.return_value = None
        mock_find.return_value = None
        mock_csv.return_value = None
        mock_plot.return_value = None

        # Создаем тестовые данные
        self.crawler.df = pd.DataFrame({
            "channels": ["Channel 1", "Channel 2"],
            "views": [100, 200],
            "comments": [5, 10],
            "forwards": [2, 4],
            "date": [datetime.now(), datetime.now()]
        })

        result = await self.crawler.crawl()

        # Проверки
        mock_start.assert_called_once()
        mock_find.assert_called_once()
        mock_csv.assert_called_once()
        mock_plot.assert_called_once()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["total_posts"], 2)
        self.assertEqual(result["channels"], 2)


if __name__ == '__main__':
    unittest.main()