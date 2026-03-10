from typing import List, Dict, Any, Optional
from datetime import datetime
from src.repositories.entry_repository import EntryRepository
from src.repositories.subcategory_repository import SubcategoryRepository


class EntryService:
    """Сервис для работы с записями"""

    def __init__(self, entry_repo: EntryRepository, subcategory_repo: SubcategoryRepository):
        self.entry_repo = entry_repo
        self.subcategory_repo = subcategory_repo

    def add_entry(self, name: str, price: float, type: str,
                  subcategory_ids: List[int] = None, date: str = None) -> Dict[str, Any]:
        """
        Добавить новую запись
        """
        if date:
            entry_date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            entry_date = datetime.now().date()

        entry = self.entry_repo.create_with_subcategories(
            name=name,
            price=price,
            type=type,
            date=entry_date,
            subcategory_ids=subcategory_ids or []
        )

        return self._entry_to_dict(entry)

    def get_recent_entries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить последние записи"""
        entries = self.entry_repo.get_recent(limit)
        return [self._entry_to_dict(e) for e in entries]

    def get_entries_by_period(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Получить записи за период"""
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        entries = self.entry_repo.get_by_date_range(start, end)
        return [self._entry_to_dict(e) for e in entries]

    def get_entries_by_type(self, type: str) -> List[Dict[str, Any]]:
        """Получить записи по типу"""
        entries = self.entry_repo.get_by_type(type)
        return [self._entry_to_dict(e) for e in entries]

    def delete_entry(self, entry_id: int) -> bool:
        """Удалить запись"""
        return self.entry_repo.delete(entry_id)

    def add_subcategory_to_entry(self, entry_id: int, subcategory_id: int) -> bool:
        """Добавить подкатегорию к записи"""
        return self.entry_repo.add_subcategory(entry_id, subcategory_id)

    def remove_subcategory_from_entry(self, entry_id: int, subcategory_id: int) -> bool:
        """Удалить подкатегорию из записи"""
        return self.entry_repo.remove_subcategory(entry_id, subcategory_id)

    def _entry_to_dict(self, entry) -> Dict[str, Any]:
        """Преобразовать запись в словарь"""
        return {
            'id': entry.id,
            'name': entry.name,
            'price': float(entry.price),
            'type': entry.type,
            'date': entry.date.strftime('%d.%m.%Y'),
            'subcategories': [
                {
                    'id': s.id,
                    'name': s.name,
                    'category_id': s.category_id,
                    'category_name': s.category.name if s.category else None
                }
                for s in entry.subcategories
            ]
        }