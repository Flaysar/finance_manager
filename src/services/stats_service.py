from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy import extract, func
from src.repositories.entry_repository import EntryRepository
from src.repositories.category_repository import CategoryRepository
from src.core.models import Entry, Subcategory, Category, entry_subcategory_table


class StatsService:
    """Сервис для статистики"""

    def __init__(self, entry_repo: EntryRepository, category_repo: CategoryRepository):
        self.entry_repo = entry_repo
        self.category_repo = category_repo
        self.db = entry_repo.db

    def get_monthly_summary(self, year: int = None, month: int = None) -> Dict[str, Any]:
        """Получить сводку за месяц"""
        if not year or not month:
            today = datetime.now()
            year = today.year
            month = today.month

        stats = self.entry_repo.get_statistics(year, month)

        # Добавляем информацию о периоде
        stats['period'] = f"{year}.{month:02d}"

        # Получаем топ категорий за месяц
        categories = self.category_repo.get_all()
        category_stats = []

        for category in categories:
            cat_stat = self.category_repo.get_category_stats(category.id)
            if cat_stat and cat_stat['total'] > 0:
                category_stats.append(cat_stat)

        # Сортируем по убыванию
        category_stats.sort(key=lambda x: x['total'], reverse=True)
        stats['top_categories'] = category_stats[:5]

        return stats

    def get_expenses_by_category(self, year: int, month: int) -> Dict[str, float]:
        """Получить распределение расходов по категориям"""
        result = self.db.query(
            Category.name,
            func.sum(Entry.price).label('total')
        ).join(
            Subcategory, Category.id == Subcategory.category_id
        ).join(
            entry_subcategory_table, Subcategory.id == entry_subcategory_table.c.subcategory_id
        ).join(
            Entry, Entry.id == entry_subcategory_table.c.entry_id
        ).filter(
            Entry.type == 'expense',
            extract('year', Entry.date) == year,
            extract('month', Entry.date) == month
        ).group_by(
            Category.name
        ).all()

        return {name: float(total) for name, total in result if total > 0}

    def get_income_by_category(self, year: int, month: int) -> Dict[str, float]:
        """Получить распределение доходов по категориям"""
        result = self.db.query(
            Category.name,
            func.sum(Entry.price).label('total')
        ).join(
            Subcategory, Category.id == Subcategory.category_id
        ).join(
            entry_subcategory_table, Subcategory.id == entry_subcategory_table.c.subcategory_id
        ).join(
            Entry, Entry.id == entry_subcategory_table.c.entry_id
        ).filter(
            Entry.type == 'income',
            extract('year', Entry.date) == year,
            extract('month', Entry.date) == month
        ).group_by(
            Category.name
        ).all()

        return {name: float(total) for name, total in result if total > 0}

    def get_year_comparison(self, year: int) -> Dict[str, Any]:
        """Сравнение по месяцам за год"""
        months_data = []

        for month in range(1, 13):
            stats = self.entry_repo.get_statistics(year, month)
            months_data.append({
                'month': month,
                'income': stats['total_income'],
                'expense': stats['total_expense'],
                'balance': stats['balance']
            })

        total_income = sum(m['income'] for m in months_data)
        total_expense = sum(m['expense'] for m in months_data)

        return {
            'year': year,
            'months': months_data,
            'total_income': total_income,
            'total_expense': total_expense,
            'total_balance': total_income - total_expense,
            'average_monthly_expense': total_expense / 12 if total_expense > 0 else 0
        }