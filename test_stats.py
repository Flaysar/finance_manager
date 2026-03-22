#!/usr/bin/env python
"""Тест для проверки функций статистики и графиков"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.append(str(project_root))

try:
    print("1. Проверка импортов...")
    from src.core.database import SessionLocal
    from src.repositories.entry_repository import EntryRepository
    from src.repositories.category_repository import CategoryRepository
    from src.services.stats_service import StatsService
    print("   ✓ Импорты успешны")
    
    print("2. Подключение к БД...")
    db = SessionLocal()
    print("   ✓ Подключение установлено")
    
    print("3. Инициализация сервисов...")
    entry_repo = EntryRepository(db)
    category_repo = CategoryRepository(db)
    stats_service = StatsService(entry_repo, category_repo)
    print("   ✓ Сервисы готовы")
    
    print("4. Получение данных статистики...")
    from datetime import datetime
    today = datetime.now()
    
    summary = stats_service.get_monthly_summary(today.year, today.month)
    print(f"   Баланс: {summary['balance']:.2f} ₽")
    print(f"   Доходы: {summary['total_income']:.2f} ₽")
    print(f"   Расходы: {summary['total_expense']:.2f} ₽")
    
    print("5. Получение распределения по категориям...")
    expenses = stats_service.get_expenses_by_category(today.year, today.month)
    income = stats_service.get_income_by_category(today.year, today.month)
    
    print(f"   Расходы по категориям: {len(expenses)} категорий")
    for cat, amount in expenses.items():
        print(f"     - {cat}: {amount:.2f} ₽")
    
    print(f"   Доходы по категориям: {len(income)} категорий")
    for cat, amount in income.items():
        print(f"     - {cat}: {amount:.2f} ₽")
    
    print("\n✓ Все тесты пройдены успешно!")
    
except Exception as e:
    print(f"\n✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    if 'db' in locals():
        db.close()
