import sys
import os
from pathlib import Path
from sqlalchemy import text  # Добавьте этот импорт

# Добавляем путь к проекту в sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from sqlalchemy.orm import Session
from src.core.database import engine, Base, SessionLocal, init_db
from src.repositories.category_repository import CategoryRepository
from src.repositories.subcategory_repository import SubcategoryRepository
from src.repositories.entry_repository import EntryRepository
from src.services.category_service import CategoryService
from src.services.entry_service import EntryService
from src.services.stats_service import StatsService
from src.ui.app import BudgetApp


def main():
    """Главная функция запуска приложения"""
    print("=" * 50)
    print("Запуск Budget App...")
    print("=" * 50)

    db = None
    try:
        # Проверка подключения к БД
        print("1. Проверка подключения к PostgreSQL...")

        # Инициализация базы данных (создание таблиц, если их нет)
        print("2. Инициализация структуры базы данных...")
        init_db()

        # Создание сессии базы данных
        print("3. Подключение к базе данных...")
        db: Session = SessionLocal()

        # Проверка соединения - ИСПРАВЛЕНО: используем text()
        db.execute(text("SELECT 1"))
        print("   ✅ Подключение успешно установлено")

        # Инициализация репозиториев
        print("4. Инициализация репозиториев...")
        category_repo = CategoryRepository(db)
        subcategory_repo = SubcategoryRepository(db)
        entry_repo = EntryRepository(db)
        print("   ✅ Репозитории созданы")

        # Инициализация сервисов
        print("5. Инициализация сервисов...")
        category_service = CategoryService(category_repo, subcategory_repo)
        entry_service = EntryService(entry_repo, subcategory_repo)
        stats_service = StatsService(entry_repo, category_repo)
        print("   ✅ Сервисы созданы")

        # Создание и запуск приложения
        print("6. Запуск пользовательского интерфейса...")
        print("=" * 50)
        app = BudgetApp(entry_service, category_service, stats_service)
        app.run()

    except Exception as e:
        print(f"❌ Ошибка при запуске приложения: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")

    finally:
        # Закрытие соединения с БД
        if db:
            db.close()
            print("\n✅ Соединение с БД закрыто")
        print("=" * 50)


if __name__ == "__main__":
    main()