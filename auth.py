# auth.py
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneNumberInvalidError, 
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError,
    AuthKeyError
)
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, session_name="UniCrawler"):
        self.api_id = os.getenv("API_ID")
        self.api_hash = os.getenv("API_HASH")
        self.phone_number = os.getenv("PHONE_NUMBER")
        self.session_name = session_name
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        self._validate_credentials()

    def _validate_credentials(self):
        missing = []
        if not self.api_id:
            missing.append("API_ID")
        if not self.api_hash:
            missing.append("API_HASH")
        if not self.phone_number:
            missing.append("PHONE_NUMBER")
        
        if missing:
            error_msg = f"Отсутствуют обязательные параметры: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    async def start(self):
        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                await self._perform_initial_auth()
            return self.client
        except AuthKeyError as e:
            logger.error("Ошибка авторизации: неверный API_ID/API_HASH")
            raise
        except Exception as e:
            logger.exception("Неизвестная ошибка при подключении")
            raise

    async def _perform_initial_auth(self):
        try:
            logger.info("Начало первичной авторизации")
            await self.client.send_code_request(self.phone_number)
            
            while True:
                code = input("Введите код из SMS: ")
                try:
                    await self.client.sign_in(phone=self.phone_number, code=code)
                    break
                except PhoneCodeInvalidError:
                    logger.warning("Неверный код. Попробуйте еще раз")
                    continue
                except PhoneCodeExpiredError:
                    logger.error("Срок действия кода истек. Запрашиваю новый код")
                    await self.client.send_code_request(self.phone_number)
                    continue

            # Обработка двухфакторной аутентификации
            if await self.client.is_user_authorized():
                return
                
            await self._handle_2fa()

        except PhoneNumberInvalidError:
            logger.error("Неверный номер телефона")
            raise
        except FloodWaitError as e:
            logger.error(f"Попробуйте снова через {e.seconds} секунд")
            raise
        except Exception as e:
            logger.exception("Ошибка при авторизации")
            raise

    async def _handle_2fa(self):
        max_attempts = 3
        attempts = 0
        
        while attempts < max_attempts:
            password = input("Введите пароль 2FA: ")
            try:
                await self.client.sign_in(password=password)
                if await self.client.is_user_authorized():
                    return
            except SessionPasswordNeededError:
                logger.error("Неверный пароль 2FA")
                attempts += 1
                if attempts >= max_attempts:
                    logger.error("Превышено количество попыток ввода пароля")
                    raise

    async def disconnect(self):
        try:
            if self.client.is_connected():
                await self.client.disconnect()
                logger.info("Сессия успешно завершена")
        except Exception as e:
            logger.error(f"Ошибка при завершении сессии: {e}")
