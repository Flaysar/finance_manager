from typing import List, Dict, Any, Optional
from src.repositories.category_repository import CategoryRepository
from src.repositories.subcategory_repository import SubcategoryRepository


class CategoryService:
    """Сервис для работы с категориями и подкатегориями"""

    def __init__(self, category_repo: CategoryRepository, subcategory_repo: SubcategoryRepository):
        self.category_repo = category_repo
        self.subcategory_repo = subcategory_repo

    def get_all_categories(self) -> List[Dict[str, Any]]:
        """Получить все категории"""
        categories = self.category_repo.get_all()
        return [self._category_to_dict(c) for c in categories]

    def get_categories_by_type(self, type: str) -> List[Dict[str, Any]]:
        """Получить категории по типу"""
        categories = self.category_repo.get_by_type(type)
        return [self._category_to_dict(c) for c in categories]

    def get_category_with_subcategories(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Получить категорию с подкатегориями"""
        category = self.category_repo.get_with_subcategories(category_id)
        if category:
            return {
                'id': category.id,
                'name': category.name,
                'type': category.type,
                'subcategories': [
                    {'id': s.id, 'name': s.name}
                    for s in category.subcategories
                ]
            }
        return None

    def create_category(self, name: str, type: str) -> Dict[str, Any]:
        """Создать категорию"""
        category = self.category_repo.create(name=name, type=type)
        return self._category_to_dict(category)

    def create_subcategory(self, name: str, category_id: int) -> Dict[str, Any]:
        """Создать подкатегорию"""
        subcategory = self.subcategory_repo.create(
            name=name,
            category_id=category_id
        )
        return {
            'id': subcategory.id,
            'name': subcategory.name,
            'category_id': subcategory.category_id
        }

    def _category_to_dict(self, category) -> Dict[str, Any]:
        return {
            'id': category.id,
            'name': category.name,
            'type': category.type,
            'subcategories': [
                {'id': s.id, 'name': s.name}
                for s in category.subcategories
            ]
        }