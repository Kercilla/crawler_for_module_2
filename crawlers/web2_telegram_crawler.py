# crawlers/web2_telegram_crawler.py
###################################
# ПОКА НИЧЕГО ИЗ ЭТОГО НЕ РАБОТАЕТ
###################################
import asyncio
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import InputMessagesFilterEmpty, MessageMediaDocument, InputPeerEmpty
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import logging
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class TelegramCrawler:
    def __init__(self, api_id, api_hash, query, max_messages=1000, delay=0.5):
        self.api_id = api_id
        self.api_hash = api_hash
        self.query = query
        self.max_messages = max_messages
        self.delay = delay
        self.client = TelegramClient('UniCrawler', api_id, api_hash)
        self.stats = {
            "total_posts": 0,
            "unique_users": set(),
            "likes": 0,
            "views": 0,
            "comments": 0,
            "forwards": 0,
            "daily_posts": defaultdict(int),
            "error_count": 0
        }

    async def start(self):
        await self.client.start()
        logger.info("Успешное подключение к Telegram API")

    async def search_messages(self):
        try:
            offset_date = datetime.now()
            while self.stats["total_posts"] < self.max_messages:
                result = await self.client(SearchRequest(
                    peer=InputPeerEmpty(),
                    q=self.query,
                    filter=InputMessagesFilterEmpty(),
                    min_date=None,
                    max_date=offset_date,
                    offset_id=0,
                    add_offset=0,
                    limit=100,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))
                
                if not result.messages:
                    logger.info("Нет новых сообщений для обработки")
                    break
                    
                for message in result.messages:
                    await self.process_message(message)
                    offset_date = message.date - timedelta(seconds=1)
                    await asyncio.sleep(self.delay * 2)
                    
        except FloodWaitError as e:
            logger.warning(f"Flood wait: {e.seconds} секунд. Ждем...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Ошибка при поиске: {str(e)}")
            self.stats["error_count"] += 1

    async def process_message(self, message):
        try:
            if message.message and self.query.lower() in message.message.lower():
                self.stats["total_posts"] += 1
                self.stats["unique_users"].add(message.sender_id)
                
                # Собираем статистику
                self.stats["likes"] += getattr(message, 'likes', 0) or 0
                self.stats["views"] += getattr(message, 'views', 0) or 0
                self.stats["forwards"] += getattr(message, 'forwards', 0) or 0
                self.stats["daily_posts"][message.date.date()] += 1
                
                # Обработка комментариев (если доступно)
                if hasattr(message, 'replies'):
                    self.stats["comments"] += message.replies.replies
                    
        except ChannelPrivateError:
            logger.warning(f"Приватный канал: {message.peer_id}")
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {str(e)}")
            self.stats["error_count"] += 1

    def generate_plot(self):
        dates = sorted(self.stats["daily_posts"].keys())
        counts = [self.stats["daily_posts"][d] for d in dates]
        
        plt.figure(figsize=(12, 6))
        plt.plot(dates, counts, marker='o', linestyle='-')
        plt.title("Количество публикаций по дням")
        plt.xlabel("Дата")
        plt.ylabel("Количество")
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig("telegram_posts.png")
        logger.info("График сохранен в telegram_posts.png")

    async def crawl(self):
        await self.start()
        await self.search_messages()
        await self.client.disconnect()
        
        return {
            "total_posts": self.stats["total_posts"],
            "unique_users": len(self.stats["unique_users"]),
            "likes": self.stats["likes"],
            "views": self.stats["views"],
            "comments": self.stats["comments"],
            "forwards": self.stats["forwards"],
            "daily_stats": self.stats["daily_posts"],
            "errors": self.stats["error_count"]
        }