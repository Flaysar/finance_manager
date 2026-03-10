from sqlalchemy import create_engine, text  # Добавьте text в импорт
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from src.core.config import settings

# Пробуем разные варианты подключения
try:
    # Сначала пробуем с обычным URL
    print("Попытка подключения с обычным URL...")
    engine = create_engine(
        settings.DATABASE_URL,
        echo=True,
        pool_size=5,
        max_overflow=10,
        client_encoding='utf8'
    )
    # Проверяем подключение - ИСПРАВЛЕНО: используем text()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Подключение с обычным URL успешно!")

except Exception as e:
    print(f"Обычный URL не сработал: {e}")
    print("Пробуем с закодированным паролем...")

    try:
        # Пробуем с закодированным паролем
        engine = create_engine(
            settings.DATABASE_URL_ENCODED,
            echo=True,
            pool_size=5,
            max_overflow=10,
            client_encoding='utf8'
        )
        # Проверяем подключение - ИСПРАВЛЕНО: используем text()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Подключение с закодированным паролем успешно!")

    except Exception as e2:
        print(f"❌ Закодированный URL тоже не сработал: {e2}")
        print("\nПробуем подключиться через libpq...")

        try:
            # Последний вариант - через libpq string
            import psycopg2

            conn = psycopg2.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASS,
                client_encoding='utf8'
            )
            conn.close()
            print("✅ Подключение через libpq успешно!")

            # Создаем engine с теми же параметрами
            engine = create_engine(
                f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?client_encoding=utf8",
                echo=True,
                pool_size=5,
                max_overflow=10
            )

        except Exception as e3:
            print(f"❌ Все способы подключения не сработали: {e3}")
            raise

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
    print("Создание таблиц в PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы успешно созданы/проверены")