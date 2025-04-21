# utils/robots_checker.py
from urllib.parse import urlparse
import logging
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class AsyncRobotsParser:
    _cache = {}  # Кеш для правил robots.txt
    
    def __init__(self):
        self.rules = {}
        self.domain = None

    @classmethod
    async def create(cls, domain: str, session: aiohttp.ClientSession):
        self = cls()
        self.domain = domain
        await self.load_robots_txt(domain, session)
        return self

    async def load_robots_txt(self, domain: str, session: aiohttp.ClientSession):
        if domain in self._cache:
            logger.debug(f"Использование кеша для {domain}")
            self.rules = self._cache[domain]
            return
        
        robots_url = f"https://{domain}/robots.txt"
        try:
            async with session.get(robots_url, timeout=5) as response:
                if response.status == 404:
                    logger.info(f"robots.txt не найден для {domain}")
                    self.rules = {'*': {'allow': [], 'disallow': []}}
                elif response.status != 200:
                    logger.warning(f"Ошибка загрузки robots.txt: {response.status}")
                    self.rules = {'*': {'allow': [], 'disallow': []}}
                else:
                    content = await response.text(errors='replace')
                    self.rules = self._parse_robots(content)
                    logger.info(f"Успешно загружен robots.txt для {domain}")
                
                self._cache[domain] = self.rules

        except aiohttp.ClientError as e:
            logger.error(f"Сетевая ошибка при загрузке {robots_url}: {str(e)}")
            self.rules = {'*': {'allow': [], 'disallow': []}}
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при загрузке {robots_url}")
            self.rules = {'*': {'allow': [], 'disallow': []}}
        except Exception as e:
            logger.exception(f"Неизвестная ошибка при обработке {robots_url}: {str(e)}")
            self.rules = {'*': {'allow': [], 'disallow': []}}

    def _parse_robots(self, content: str) -> dict:
        rules = {'*': {'allow': [], 'disallow': []}}
        current_agent = '*'
        
        try:
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Безопасное разделение строки
                parts = list(map(str.strip, line.split(':', 1)))
                if len(parts) != 2:
                    logger.warning(f"Некорректная строка в robots.txt: {line}")
                    continue
                
                key, value = parts[0].lower(), parts[1]
                
                if key == 'user-agent':
                    current_agent = value.lower() if value else '*'
                    if current_agent not in rules:
                        rules[current_agent] = {'allow': [], 'disallow': []}
                elif key in ('allow', 'disallow'):
                    path = value.strip()
                    if not path.startswith('/'):
                        path = '/' + path  # Нормализация путей
                    rules[current_agent][key].append(path)
        except Exception as e:
            logger.error(f"Критическая ошибка парсинга robots.txt: {str(e)}")
            return {'*': {'allow': [], 'disallow': []}}
        
        return rules

    def can_fetch(self, user_agent: str, url: str) -> bool:
        try:
            parsed_url = urlparse(url)
            path = parsed_url.path
            
            # Проверяем специфичные правила для User-Agent
            if user_agent in self.rules:
                agent_rules = self.rules[user_agent]
                if self._check_rules(agent_rules, path):
                    return True
            
            # Проверяем общие правила
            general_rules = self.rules.get('*', {})
            return self._check_rules(general_rules, path)
        
        except Exception as e:
            logger.error(f"Ошибка проверки доступа для {url}: {str(e)}")
            return False  # Запрещаем доступ при ошибках

    def _check_rules(self, rules: dict, path: str) -> bool:
        allow = rules.get('allow', [])
        disallow = rules.get('disallow', [])
        
        # Алгоритм согласно спецификации:
        # 1. Проверяем наиболее специфичные правила
        # 2. Разрешающие правила имеют приоритет над запрещающими
        longest_match = None
        for rule in allow + disallow:
            if path.startswith(rule):
                if longest_match is None or len(rule) > len(longest_match):
                    longest_match = rule
        
        if longest_match is None:
            return True  # Нет правил - доступ разрешен
        
        return longest_match in allow

async def check_robots_txt_async(
    url: str, 
    domain: str, 
    session: aiohttp.ClientSession,
    user_agent: str = "*"
) -> bool:
    try:
        parsed_url = urlparse(url)
        robots_parser = await AsyncRobotsParser.create(domain, session)
        return robots_parser.can_fetch(user_agent, parsed_url.path)
    except Exception as e:
        logger.error(f"Критическая ошибка проверки robots.txt для {url}: {str(e)}")
        return False  # Запрещаем доступ при любых ошибках