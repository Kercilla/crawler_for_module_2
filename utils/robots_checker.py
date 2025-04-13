# utils/robots_checker.py
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class AsyncRobotsParser:
    _cache = {}
    
    def __init__(self):
        self.rules = {}

    @classmethod
    async def create(cls, domain, session):
        self = cls()
        await self.load_robots_txt(domain, session)
        return self

    async def load_robots_txt(self, domain, session):
        if domain in self._cache:
            self.rules = self._cache[domain]
            return
        
        robots_url = f"https://{domain}/robots.txt"
        try:
            async with session.get(robots_url, timeout=5) as response:
                if response.status != 200:
                    self.rules = {}
                    return
                
                content = await response.text()
                self.rules = self._parse_robots(content)
                self._cache[domain] = self.rules
                logger.info(f"Загружен robots.txt для {domain}")
        
        except Exception as e:
            logger.warning(f"Не удалось загрузить robots.txt для {domain}: {str(e)}")
            self.rules = {}

    def _parse_robots(self, content):
        rules = {'*': {'allow': [], 'disallow': []}}
        current_agent = '*'
        
        for line in content.splitlines():
            line = line.strip().lower()
            if not line or line.startswith('#'):
                continue
                
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
                
            key, value = parts[0].strip(), parts[1].strip()
            
            if key == 'user-agent':
                current_agent = value if value else '*'
                if current_agent not in rules:
                    rules[current_agent] = {'allow': [], 'disallow': []}
            elif key in ('allow', 'disallow'):
                if current_agent == '*':
                    rules['*'][key].append(value)
                else:
                    rules[current_agent][key].append(value)
        
        return rules

    def can_fetch(self, user_agent, url):
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Проверяем специфичные правила для User-Agent
        if user_agent in self.rules:
            agent_rules = self.rules[user_agent]
            for disallow in agent_rules['disallow']:
                if path.startswith(disallow):
                    return False
            for allow in agent_rules['allow']:
                if path.startswith(allow):
                    return True
        
        # Проверяем общие правила
        general_rules = self.rules.get('*', {})
        for disallow in general_rules['disallow']:
            if path.startswith(disallow):
                return False
        for allow in general_rules['allow']:
            if path.startswith(allow):
                return True
        
        return True

async def check_robots_txt_async(url, domain, session, user_agent="*"):
    try:
        parsed_url = urlparse(url)
        robots_parser = await AsyncRobotsParser.create(domain, session)
        return robots_parser.can_fetch(user_agent, parsed_url.path)
    except Exception as e:
        logger.error(f"Ошибка проверки robots.txt для {url}: {str(e)}")
        return True  # В случае ошибки считаем доступ разрешенным