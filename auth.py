# auth.py
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv
import os

load_dotenv()

class AuthManager:
    def __init__(self, session_name="UniCrawler"):
        self.api_id = os.getenv("API_ID")
        self.api_hash = os.getenv("API_HASH")
        self.phone_number = os.getenv("PHONE_NUMBER")
        self.session_name = session_name
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)

    async def start(self):
        """Начало сессии и аутентификация"""
        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID или API_HASH не найдены в .env файле")

        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self._perform_initial_auth()
        return self.client

    async def _perform_initial_auth(self):
        """Первичная авторизация"""
        print("Первичная авторизация. Введите код из SMS.")
        await self.client.send_code_request(self.phone_number)
        code = input("Введите код из SMS: ")
        try:
            await self.client.sign_in(phone=self.phone_number, code=code)
        except SessionPasswordNeededError:
            print("\nВключена двухфакторная аутентификация!\n"
            "Введите пароль двухфакторной аутентификации:")
            password = input("Пароль: ")
            await self.client.sign_in(password=password)
        
    async def disconnect(self):
        """Завершение сессии"""
        await self.client.disconnect()