import asyncio
from telethon.errors import (
    FloodWaitError,
    ChannelPrivateError,
    MsgIdInvalidError,
    AuthKeyError,
    ApiIdInvalidError
)
from telethon.tl.functions.messages import GetHistoryRequest
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
import logging
from auth import AuthManager
import pandas as pd
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class TelegramCrawler:
    def __init__(self, max_messages=100, delay=0.2):
        self.df = pd.DataFrame()
        self.max_messages = max_messages
        self.delay = delay
        self.auth_manager = AuthManager()
        self.client = None
        self.stats = {
            "channels": [],
            "university": [],
            "messages": [],
            "views": [],
            "comments": [],
            "forwards": [],
            "date": []
        }
        self._validate_parameters()

    def _validate_parameters(self):
        if self.max_messages <= 0:
            raise ValueError("Максимальное количество сообщений должно быть > 0")
        if self.delay < 0:
            raise ValueError("Задержка не может быть отрицательной")

    async def start(self):
        try:
            self.client = await self.auth_manager.start()
            logger.info("Успешное подключение к Telegram API")
        except (AuthKeyError, ApiIdInvalidError) as e:
            logger.error("Ошибка аутентификации: проверьте API_ID и API_HASH")
            raise
        except Exception as e:
            logger.exception("Ошибка инициализации клиента Telegram")
            raise

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
                    try:
                        await asyncio.sleep(self.delay)
                        dialog_name = dialog.name.lower()
                        if any(name.lower() in dialog_name for name in names):
                            logger.info(f"Найден канал/группа: {dialog.name}")
                            await self.search_messages(dialog, dialog.name, university)
                    except ChannelPrivateError:
                        logger.warning(f"Доступ к каналу {dialog.name} запрещен")
                    except Exception as e:
                        logger.error(f"Ошибка обработки диалога {dialog.name}: {str(e)}")

        except FloodWaitError as e:
            logger.error(f"Telegram FloodWait: ждем {e.seconds} секунд")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.exception("Критическая ошибка при поиске каналов")
            raise

    async def search_messages(self, dialog, channel, university):
        try:
            offset_date = datetime.now(timezone.utc) - timedelta(days=30)
            
            result = await self.client(GetHistoryRequest(
                peer=dialog.id,
                offset_id=0,
                offset_date=offset_date,
                add_offset=0,
                limit=min(self.max_messages, 100),  # Telegram API limit
                max_id=0,
                min_id=0,
                hash=0
            ))

            if not result.messages:
                logger.info(f"Нет сообщений для {channel}")
                return

            for i, message in enumerate(result.messages):
                if i >= self.max_messages:
                    break
                try:
                    await self.process_message(message, channel, university)
                    await asyncio.sleep(self.delay)
                except Exception as e:
                    logger.error(f"Ошибка обработки сообщения {message.id}: {str(e)}")

        except (FloodWaitError, MsgIdInvalidError) as e:
            logger.warning(f"Telegram API error: {e}")
            await asyncio.sleep(self.delay * 5)
        except Exception as e:
            logger.exception(f"Критическая ошибка при получении истории {channel}")
            raise

    async def process_message(self, message, channel, university):
        try:
            self.stats["university"].append(university)
            self.stats["channels"].append(channel) 
            self.stats['messages'].append(getattr(message, 'message', ''))
            
            # Безопасное получение числовых данных
            self.stats["views"].append(getattr(message, 'views', 0) or 0)
            self.stats["forwards"].append(getattr(message, 'forwards', 0) or 0)
            self.stats["date"].append(message.date.astimezone(timezone.utc))
            
            # Обработка комментариев
            comments = 0
            if hasattr(message, 'replies') and message.replies:
                comments = getattr(message.replies, 'replies', 0) or 0
            self.stats["comments"].append(comments)

        except AttributeError as e:
            logger.error(f"Ошибка доступа к атрибуту в сообщении {message.id}: {str(e)}")
        except Exception as e:
            logger.exception(f"Неизвестная ошибка обработки сообщения {message.id}")
            raise

    def generate_plot(self):
        try:
            if self.df.empty:
                logger.warning("Нет данных для построения графика")
                return

            self.df['date'] = pd.to_datetime(self.df['date']).dt.date
            daily_posts = self.df.groupby(['university', 'date']).size().unstack(level=0, fill_value=0)
            
            plt.figure(figsize=(16, 10))
            ax = daily_posts.plot(
                kind='line',
                marker='o',
                linewidth=1,
                markersize=5,
                title='Количество публикаций по дням'
            )
            
            ax.set_xlabel('Дата')
            ax.set_ylabel('Количество публикаций')
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend(title='Университет')
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            os.makedirs('plots', exist_ok=True)
            plt.savefig('plots/daily_posts.png', dpi=300, bbox_inches='tight')
            logger.info("График сохранен в plots/daily_posts.png")

        except Exception as e:
            logger.error(f"Ошибка генерации графика: {str(e)}")
            raise

    def save_to_csv(self):
        try:
            if not self.stats["messages"]:
                logger.warning("Нет данных для сохранения")
                return
                
            self.df = pd.DataFrame(self.stats)
            os.makedirs('data', exist_ok=True)
            self.df.to_csv('data/Telegram_posts.csv', index=False, encoding='utf-8')
            logger.info("Данные сохранены в data/Telegram_posts.csv")

        except Exception as e:
            logger.error(f"Ошибка сохранения CSV: {str(e)}")
            raise

    async def crawl(self):
        try:
            await self.start()
            await self.find_channels()
            self.save_to_csv()
            self.generate_plot()
            
        except KeyboardInterrupt:
            logger.info("Процесс прерван пользователем")
        except Exception as e:
            logger.exception("Критическая ошибка в процессе краулинга")
        finally:
            if self.client:
                try:
                    await self.auth_manager.disconnect()
                except Exception as e:
                    logger.error(f"Ошибка закрытия сессии: {str(e)}")

        return {
            "total_posts": len(self.df),
            "channels": self.df['channels'].nunique() if not self.df.empty else 0,
            "views": self.df['views'].mean() if not self.df.empty else 0,
            "comments": self.df["comments"].mean() if not self.df.empty else 0,
            "forwards": self.df["forwards"].mean() if not self.df.empty else 0,
            "date_range": (self.stats["date"][0].strftime('%Y-%m-%d'), 
                         self.stats["date"][-1].strftime('%Y-%m-%d')) if self.stats["date"] else None
        }