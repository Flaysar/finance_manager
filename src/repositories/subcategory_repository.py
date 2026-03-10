from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.core.models import Subcategory, Entry, entry_subcategory_table
from src.repositories.base_repository import BaseRepository


class SubcategoryRepository(BaseRepository[Subcategory]):
    """Репозиторий для работы с подкатегориями"""

    def __init__(self, db: Session):
        super().__init__(Subcategory, db)

    def get_by_category(self, category_id: int) -> List[Subcategory]:
        """Получить подкатегории по категории"""
        return self.db.query(Subcategory).filter(Subcategory.category_id == category_id).all()

    def get_with_entries(self, subcategory_id: int) -> Optional[Subcategory]:
        """Получить подкатегорию вместе с записями"""
        return self.db.query(Subcategory).filter(Subcategory.id == subcategory_id).first()

    def get_subcategory_stats(self, subcategory_id: int) -> dict:
        """Получить статистику по подкатегории"""
        subcategory = self.get_by_id(subcategory_id)
        if not subcategory:
            return {}

        # Сумма по всем записям в этой подкатегории
        total = self.db.query(func.sum(Entry.price)). \
                    join(entry_subcategory_table, Entry.id == entry_subcategory_table.c.entry_id). \
                    filter(entry_subcategory_table.c.subcategory_id == subcategory_id). \
                    scalar() or 0

        # Количество записей
        count = self.db.query(func.count(Entry.id.distinct())). \
                    join(entry_subcategory_table, Entry.id == entry_subcategory_table.c.entry_id). \
                    filter(entry_subcategory_table.c.subcategory_id == subcategory_id). \
                    scalar() or 0

        return {
            'subcategory_id': subcategory_id,
            'subcategory_name': subcategory.name,
            'category_id': subcategory.category_id,
            'total': float(total),
            'entries_count': count
        }