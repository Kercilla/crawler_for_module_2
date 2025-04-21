import asyncio
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import GetHistoryRequest
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
import logging
from auth import AuthManager
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class TelegramCrawler:
    def __init__(self, max_messages=1000, delay=0.2):
        self.df = None
        self.max_messages = max_messages
        self.delay = delay
        self.auth_manager = AuthManager()
        self.client = None
        self.stats = {
            "university": [],
            "messages": [],
            "views": [],
            "comments": [],
            "forwards": [],
            "date": []
        }

    async def start(self):
        """Инициализация клиента через AuthManager"""
        self.client = await self.auth_manager.start()
        logger.info("Успешное подключение к Telegram API")

    async def find_channels(self):
        SEARCH_KEYWORDS = {
            'МГУ': [
                'МГУ', 'Московский государственный университет',
                'МГУ им. Ломоносова', 'Московский университет',
                'MSU', 'Lomonosov Moscow State University'
            ],
            'СПбГУ': [
                'СПбГУ', 'Санкт-Петербургский государственный университет',
                'Санкт-Петербургский университет', 'СПб университет',
                'SPbU', 'Saint Petersburg State University'
            ]
        }

        try:
            for university, names in SEARCH_KEYWORDS.items():
                logger.info(f"Поиск каналов для {university}")
                
                async for dialog in self.client.iter_dialogs():
                    #await asyncio.sleep(self.delay)  
                    dialog_name = dialog.name.lower()
                    if any(name.lower() in dialog_name for name in names):
                        logger.info(f"Найден канал/группа: {dialog.name}")
                        await self.search_messages(dialog, university)

        except Exception as e:
            logger.error(f"Ошибка поиска каналов: {str(e)}")

    async def search_messages(self, dialog, university):
        try:
            offset_date = datetime.now(timezone.utc) - timedelta(days=60)
            
            result = await self.client(GetHistoryRequest(
                peer=dialog.id,
                offset_id=0,
                offset_date=offset_date,
                add_offset=0,
                limit= self.max_messages,
                max_id=0,
                min_id=0,
                hash=0
            ))

            if not result.messages:
                logger.info("Нет новых сообщений для обработки")
                return

            for i, message in enumerate(result.messages):
                if i >= self.max_messages:
                    break  

                await self.process_message(message, university)
                #await asyncio.sleep(self.delay)

        except FloodWaitError as e:
            logger.warning(f"Flood wait: {e.seconds} секунд. Ждем...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Ошибка при поиске: {str(e)}")

    async def process_message(self, message, university):
        try:
            self.stats["university"].append(university) 
            self.stats['messages'].append(getattr(message, 'message', ''))
            self.stats["views"].append(getattr(message, 'views', 0))
            self.stats["forwards"].append(getattr(message, 'forwards', 0))
            self.stats["date"].append(message.date)
            
            comments = 0
            if hasattr(message, 'replies') and message.replies:
                comments = getattr(message.replies, 'replies', 0)
            self.stats["comments"].append(comments)

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {str(e)}")

    def generate_plot(self):

        self.df['date'] = pd.to_datetime(self.df['date']).dt.date
        daily_posts = self.df.groupby(['university', 'date']).size().unstack(level=0)
        
        plt.figure(figsize=(16, 10))
        daily_posts.plot(kind='line', marker='o', linewidth=1, markersize=5)
        plt.title('Количество публикаций по дням', fontsize=14, pad=20)
        plt.xlabel('Дата', fontsize=10)
        plt.ylabel('Количество публикаций', fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(title='Университет', fontsize=10)
        
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d.%m.%Y'))
        plt.gcf().autofmt_xdate()  
        
        plt.tight_layout()
        plt.savefig('daily_posts.png', dpi=300, bbox_inches='tight')  

    def save_to_csv(self):
            
            self.df = pd.DataFrame(self.stats)
            self.df.to_csv('Telegram_posts.csv', index=False, encoding='utf-8')
            logger.info("Данные сохранены в Telegram_posts.csv")

    async def crawl(self):
        try:
            await self.start()
            await self.find_channels()
            self.save_to_csv()
            self.generate_plot()
        finally:
            if self.client:
                await self.auth_manager.disconnect()

        return {
            "total_posts": len(self.df),
            "university": self.df['university'].nunique(),
            "views": self.df['views'].mean(),
            "comments": self.df["comments"].mean(),
            "forwards": self.df["forwards"].mean(),
            "date": self.stats["date"]
        }

    