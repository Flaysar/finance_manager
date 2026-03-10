import os
from dotenv import load_dotenv
import urllib.parse
import sys

# Загружаем переменные окружения из .env файла
load_dotenv()


class Settings:
    # PostgreSQL
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "budget_app")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASS = os.getenv("DB_PASS", "123")

    # Application
    APP_NAME = os.getenv("APP_NAME", "Budget App")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

    @property
    def DATABASE_URL(self):
        # Простой вариант без кодирования - если пароль простой
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DATABASE_URL_ENCODED(self):
        # Кодируем пароль для безопасной передачи в URL
        encoded_password = urllib.parse.quote_plus(self.DB_PASS)
        return f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()

# Для отладки - выводим информацию о подключении (без пароля)
print(f"Подключение к PostgreSQL: {settings.DB_USER}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")