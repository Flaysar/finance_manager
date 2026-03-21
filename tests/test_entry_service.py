import importlib.util
import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest


def _load_entry_service_class():
    repositories_pkg = ModuleType("src.repositories")
    entry_repo_module = ModuleType("src.repositories.entry_repository")
    subcategory_repo_module = ModuleType("src.repositories.subcategory_repository")

    class EntryRepository:  
        pass

    class SubcategoryRepository:  
        pass

    entry_repo_module.EntryRepository = EntryRepository
    subcategory_repo_module.SubcategoryRepository = SubcategoryRepository

    sys.modules["src.repositories"] = repositories_pkg
    sys.modules["src.repositories.entry_repository"] = entry_repo_module
    sys.modules["src.repositories.subcategory_repository"] = subcategory_repo_module

    service_path = Path(__file__).resolve().parents[1] / "src" / "services" / "entry_service.py"
    spec = importlib.util.spec_from_file_location("isolated_entry_service", service_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.EntryService


@pytest.mark.testcase("TC-ADD-ENTRY-001")
def test_add_entry_creates_entry_with_selected_subcategories_and_formats_output():
    EntryService = _load_entry_service_class()
    entry_repo = Mock()
    subcategory_repo = Mock()
    service = EntryService(entry_repo=entry_repo, subcategory_repo=subcategory_repo)

    category = SimpleNamespace(id=1, name="Продукты", type="expense")
    subcategory = SimpleNamespace(id=10, name="Овощи", category_id=1, category=category)
    created_entry = SimpleNamespace(
        id=7,
        name="Покупка в магазине",
        price=Decimal("450.75"),
        type="expense",
        date=date(2026, 3, 21),
        subcategories=[subcategory],
    )
    entry_repo.create_with_subcategories.return_value = created_entry

    result = service.add_entry(
        name="Покупка в магазине",
        price=450.75,
        type="expense",
        subcategory_ids=[10],
        date="2026-03-21",
    )

    entry_repo.create_with_subcategories.assert_called_once_with(
        name="Покупка в магазине",
        price=450.75,
        type="expense",
        date=date(2026, 3, 21),
        subcategory_ids=[10],
    )
    assert result["id"] == 7
    assert result["name"] == "Покупка в магазине"
    assert result["price"] == 450.75
    assert result["type"] == "expense"
    assert result["date"] == "21.03.2026"
    assert result["subcategories"] == [
        {
            "id": 10,
            "name": "Овощи",
            "category_id": 1,
            "category_name": "Продукты",
        }
    ]


@pytest.mark.testcase("TC-ADD-ENTRY-NEG-001")
def test_add_entry_raises_value_error_for_invalid_date_format():
    EntryService = _load_entry_service_class()
    entry_repo = Mock()
    subcategory_repo = Mock()
    service = EntryService(entry_repo=entry_repo, subcategory_repo=subcategory_repo)

    with pytest.raises(ValueError):
        service.add_entry(
            name="Покупка",
            price=100.0,
            type="expense",
            subcategory_ids=[10],
            date="21-03-2026",
        )

    entry_repo.create_with_subcategories.assert_not_called()

