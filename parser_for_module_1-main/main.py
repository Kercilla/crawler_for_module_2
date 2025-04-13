# main.py
import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import argparse
from crawlers.web1_crawler import Web1Crawler
from crawlers.web2_telegram_crawler import TelegramCrawler
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

async def run_web1(domain, max_pages, max_depth, delay, concurrency):
    async with Web1Crawler(
        start_url=f"https://{domain}",
        domain=domain,
        max_pages=max_pages,
        max_depth=max_depth,
        delay=delay,
        concurrency=concurrency
    ) as crawler:
        stats = await crawler.crawl()
        print("\n=== ИТОГОВАЯ СТАТИСТИКА ===")
        print(f"Обработано страниц: {stats['total_pages']}")
        print(f"Внутренние страницы: {stats['internal_pages']}")
        print(f"Ошибочные ссылки: {len(stats['error_links'])}")
        print(f"Поддомены: {len(stats['subdomains'])}")
        print(f"Внешние ресурсы: Общее количество: {stats['external_links']['total']}, Уникальные: {len(stats['external_links']['unique'])}")
        print(f"Файлы: {stats['files']['total']} (PDF: {stats['files']['pdf']}, DOC: {stats['files']['doc']}, DOCX: {stats['files']['docx']})")

async def run_web2(api_id: int, api_hash: str, query: str, max_messages: int):
    crawler = TelegramCrawler(
        api_id=api_id,
        api_hash=api_hash,
        query=query,
        max_messages=max_messages
    )
    stats = await crawler.crawl()
    crawler.generate_plot()
    
    print("\n=== Статистика Telegram ===")
    print(f"Всего публикаций: {stats['total_posts']}")
    print(f"Уникальных пользователей: {stats['unique_users']}")
    print(f"Лайки: {stats['likes']}")
    print(f"Просмотры: {stats['views']}")
    print(f"Комментарии: {stats['comments']}")
    print(f"Репосты: {stats['forwards']}")
    print(f"Ошибок: {stats['errors']}")
    print("============================")

def main():
    parser = argparse.ArgumentParser(description="Поисковый робот для Web 1.0/Web 2.0")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Web 1.0 parser
    web1_parser = subparsers.add_parser("web1", help="Запуск краулера для Web 1.0")
    web1_parser.add_argument("--domain", required=True, help="Домен для обхода (spbu.ru/msu.ru)")
    web1_parser.add_argument("--max-pages", type=int, default=500, help="Максимальное количество страниц")
    web1_parser.add_argument("--max-depth", type=int, default=3, help="Максимальная глубина обхода")
    web1_parser.add_argument("--delay", type=float, default=0.5, help="Задержка между запросами")
    web1_parser.add_argument("--concurrency", type=int, default=10, help="Количество параллельных запросов")

    # Web 2.0 parser
    web2_parser = subparsers.add_parser("web2", help="Запуск краулера для Web 2.0 (Telegram)")
    web2_parser.add_argument("--api-id", type=int, required=True, help="Telegram API ID")
    web2_parser.add_argument("--api-hash", required=True, help="Telegram API Hash")
    web2_parser.add_argument("--query", required=True, help="Поисковый запрос (например 'СПбГУ')")
    web2_parser.add_argument("--max-messages", type=int, default=100, help="Максимальное количество сообщений")

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
            api_id=args.api_id,
            api_hash=args.api_hash,
            query=args.query,
            max_messages=args.max_messages
        ))

if __name__ == "__main__":
    main()