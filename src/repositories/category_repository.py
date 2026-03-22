from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.core.models import Category, Subcategory, Entry, entry_subcategory_table
from src.repositories.base_repository import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Репозиторий для работы с категориями"""

    def __init__(self, db: Session):
        super().__init__(Category, db)

    def get_by_type(self, type: str) -> List[Category]:
        """Получить категории по типу (income/expense)"""
        return self.db.query(Category).filter(Category.type == type).all()

    def get_with_subcategories(self, category_id: int) -> Optional[Category]:
        """Получить категорию вместе с подкатегориями"""
        return self.db.query(Category).filter(Category.id == category_id).first()

    def get_category_stats(self, category_id: int) -> dict:
        """Получить статистику по категории"""
        category = self.get_by_id(category_id)
        if not category:
            return {}

        # Сумма по всем записям в этой категории (через подкатегории)
        total = self.db.query(func.sum(Entry.price)). \
                    join(entry_subcategory_table, Entry.id == entry_subcategory_table.c.entry_id). \
                    join(Subcategory, Subcategory.id == entry_subcategory_table.c.subcategory_id). \
                    filter(Subcategory.category_id == category_id). \
                    scalar() or 0

        # Количество записей
        count = self.db.query(func.count(Entry.id.distinct())). \
                    join(entry_subcategory_table, Entry.id == entry_subcategory_table.c.entry_id). \
                    join(Subcategory, Subcategory.id == entry_subcategory_table.c.subcategory_id). \
                    filter(Subcategory.category_id == category_id). \
                    scalar() or 0

        return {
            'category_id': category_id,
            'category_name': category.name,
            'total': float(total),
            'entries_count': count
        }