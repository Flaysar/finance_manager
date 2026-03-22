from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from src.core.config import settings
import sys

# Определяем, находимся ли мы в тестовой среде
is_testing = 'pytest' in sys.modules or 'unittest' in sys.modules

# Создаем engine без проверки подключения (для совместимости с тестами)
# echo отключаем в тестовой среде для избежания ошибок подключения
engine = create_engine(
    settings.DATABASE_URL,
    echo=not is_testing,  # Отключаем echo в тестовой среде
    pool_size=5,
    max_overflow=10,
    client_encoding='utf8',
    pool_pre_ping=True,  # Проверяем соединение перед использованием
    connect_args={'check_same_thread': False} if 'sqlite' in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def init_db():
    """Создает все таблицы в базе данных (если их нет)"""
    try:
        print("Создание таблиц в PostgreSQL...")
        Base.metadata.create_all(bind=engine)
        print("✅ Таблицы успешно созданы/проверены")
    except Exception as e:
        print(f"⚠️  Ошибка при создании таблиц: {e}")
        print("Это может быть нормально в тестовой среде (CI/CD)")