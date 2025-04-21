import asyncio
from dotenv import load_dotenv
import os
import argparse
from crawlers.web1_crawler import Web1Crawler
from crawlers.web2_telegram_crawler import TelegramCrawler
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def run_web1(domain, max_pages, max_depth, delay, concurrency):
    try:
        async with Web1Crawler(
            start_url=f"https://{domain}",
            domain=domain,
            max_pages=max_pages,
            max_depth=max_depth,
            delay=delay,
            concurrency=concurrency
        ) as crawler:
            stats = await crawler.crawl()
            
            if "error" in stats:
                logger.error(f"Краулер завершился с ошибкой: {stats['error']}")
                return
                
            print("\n=== ИТОГОВАЯ СТАТИСТИКА ===")
            print(f"Обработано страниц: {stats['total_pages']}")
            print(f"Внутренние страницы: {stats['internal_pages']}")
            print(f"Ошибочные ссылки: {len(stats['error_links'])}")
            print(f"Поддомены: {len(stats['subdomains'])}")
            print(f"Внешние ресурсы: Общее количество: {stats['external_links']['total']}, "
                  f"Уникальные: {len(stats['external_links']['unique'])}")
            print(f"Файлы: {stats['files']['total']} (PDF: {stats['files']['pdf']}, "
                  f"DOC: {stats['files']['doc']}, DOCX: {stats['files']['docx']})")
                  
    except ValueError as e:
        logger.error(f"Ошибка валидации параметров: {e}")
    except Exception as e:
        logger.exception("Произошла критическая ошибка в Web1Crawler")

async def run_web2(max_messages: int):
    try:
        api_id = os.getenv("API_ID")
        api_hash = os.getenv("API_HASH")
        
        if not api_id or not api_hash:
            raise ValueError("Отсутствуют учетные данные Telegram API")
        
        crawler = TelegramCrawler(
            max_messages=max_messages
        )
        stats = await crawler.crawl()

        print("\n=== Статистика Telegram ===")
        print(f"Всего публикаций: {stats.get('total_posts', 0)}")
        print(f"Уникальных групп: {stats.get('channels', [])}")
        print(f"Просмотры: {stats.get('views', 0)}")
        print(f"Комментарии: {stats.get('comments', 0)}")
        print(f"Репосты: {stats.get('forwards', 0)}")
        print("============================")
        
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
    except Exception as e:
        logger.exception("Произошла критическая ошибка в TelegramCrawler")

def main():
    try:
        parser = argparse.ArgumentParser(description="Поисковый робот для Web 1.0/Web 2.0")
        subparsers = parser.add_subparsers(dest="command", required=True)

        # Web 1.0 parser
        web1_parser = subparsers.add_parser("web1", help="Запуск краулера для Web 1.0")
        web1_parser.add_argument("--domain", required=True, 
                               help="Домен для обхода (spbu.ru/msu.ru)")
        web1_parser.add_argument("--max-pages", type=int, default=500, 
                                help="Максимальное количество страниц")
        web1_parser.add_argument("--max-depth", type=int, default=3, 
                                help="Максимальная глубина обхода")
        web1_parser.add_argument("--delay", type=float, default=0.5, 
                                help="Задержка между запросами")
        web1_parser.add_argument("--concurrency", type=int, default=10, 
                                help="Количество параллельных запросов")

        # Web 2.0 parser
        web2_parser = subparsers.add_parser("web2", help="Запуск краулера для Web 2.0 (Telegram)")
        web2_parser.add_argument("--max-messages", type=int, default=100, 
                                help="Максимальное количество сообщений")

        args = parser.parse_args()

        if args.command == "web1":
            asyncio.run(run_web1(
                domain=args.domain,
                max_pages=args.max_pages,
                max_depth=args.max_depth,
                delay=args.delay,
                concurrency=args.concurrency
            ))
        elif args.command == "web2":
            asyncio.run(run_web2(
                max_messages=args.max_messages
            ))
            
    except argparse.ArgumentError as e:
        logger.error(f"Ошибка в аргументах командной строки: {e}")
        parser.print_help()
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.exception("Непредвиденная ошибка в основной функции")

if __name__ == "__main__":
    main()