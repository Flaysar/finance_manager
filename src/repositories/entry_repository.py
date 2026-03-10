from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from src.core.models import Entry, Subcategory, entry_subcategory_table
from src.repositories.base_repository import BaseRepository


class EntryRepository(BaseRepository[Entry]):
    """Репозиторий для работы с записями"""

    def __init__(self, db: Session):
        super().__init__(Entry, db)

    def get_by_date_range(self, start_date: date, end_date: date) -> List[Entry]:
        """Получить записи за период"""
        return self.db.query(Entry).filter(
            and_(
                Entry.date >= start_date,
                Entry.date <= end_date
            )
        ).order_by(Entry.date.desc()).all()

    def get_by_type(self, type: str, limit: int = 100) -> List[Entry]:
        """Получить записи по типу"""
        return self.db.query(Entry).filter(
            Entry.type == type
        ).order_by(Entry.date.desc()).limit(limit).all()

    def get_recent(self, limit: int = 20) -> List[Entry]:
        """Получить последние записи"""
        return self.db.query(Entry).order_by(
            Entry.date.desc(),
            Entry.created_at.desc()
        ).limit(limit).all()

    def create_with_subcategories(self, name: str, price: float, type: str,
                                  date: date, subcategory_ids: List[int]) -> Entry:
        """Создать запись и привязать к подкатегориям"""
        entry = self.create(
            name=name,
            price=price,
            type=type,
            date=date
        )

        # Добавляем связи с подкатегориями
        if subcategory_ids:
            for subcategory_id in subcategory_ids:
                self.db.execute(
                    entry_subcategory_table.insert().values(
                        entry_id=entry.id,
                        subcategory_id=subcategory_id
                    )
                )
            self.db.commit()
            self.db.refresh(entry)

        return entry

    def add_subcategory(self, entry_id: int, subcategory_id: int) -> bool:
        """Добавить подкатегорию к записи"""
        # Проверяем, существует ли уже такая связь
        exists = self.db.execute(
            entry_subcategory_table.select().where(
                and_(
                    entry_subcategory_table.c.entry_id == entry_id,
                    entry_subcategory_table.c.subcategory_id == subcategory_id
                )
            )
        ).first()

        if not exists:
            self.db.execute(
                entry_subcategory_table.insert().values(
                    entry_id=entry_id,
                    subcategory_id=subcategory_id
                )
            )
            self.db.commit()
            return True
        return False

    def remove_subcategory(self, entry_id: int, subcategory_id: int) -> bool:
        """Удалить подкатегорию из записи"""
        result = self.db.execute(
            entry_subcategory_table.delete().where(
                and_(
                    entry_subcategory_table.c.entry_id == entry_id,
                    entry_subcategory_table.c.subcategory_id == subcategory_id
                )
            )
        )
        self.db.commit()
        return result.rowcount > 0

    def get_subcategories(self, entry_id: int) -> List[Subcategory]:
        """Получить все подкатегории записи"""
        entry = self.get_by_id(entry_id)
        if entry:
            return entry.subcategories
        return []

    def get_statistics(self, year: int = None, month: int = None) -> Dict[str, Any]:
        """Получить статистику"""
        query = self.db.query(Entry)

        if year and month:
            query = query.filter(
                extract('year', Entry.date) == year,
                extract('month', Entry.date) == month
            )
        elif year:
            query = query.filter(extract('year', Entry.date) == year)

        # Общая сумма доходов
        total_income = query.filter(Entry.type == 'income').with_entities(
            func.sum(Entry.price)
        ).scalar() or 0

        # Общая сумма расходов
        total_expense = query.filter(Entry.type == 'expense').with_entities(
            func.sum(Entry.price)
        ).scalar() or 0

        # Количество записей
        entry_count = query.count()

        return {
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'balance': float(total_income - total_expense),
            'entry_count': entry_count
        }