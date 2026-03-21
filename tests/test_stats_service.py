import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


def _load_stats_service_class():
    repositories_pkg = ModuleType("src.repositories")
    entry_repo_module = ModuleType("src.repositories.entry_repository")
    category_repo_module = ModuleType("src.repositories.category_repository")

    class EntryRepository:  
        pass

    class CategoryRepository:
        pass

    entry_repo_module.EntryRepository = EntryRepository
    category_repo_module.CategoryRepository = CategoryRepository

    sys.modules["src.repositories"] = repositories_pkg
    sys.modules["src.repositories.entry_repository"] = entry_repo_module
    sys.modules["src.repositories.category_repository"] = category_repo_module

    service_path = Path(__file__).resolve().parents[1] / "src" / "services" / "stats_service.py"
    spec = importlib.util.spec_from_file_location("isolated_stats_service", service_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.StatsService


@pytest.mark.testcase("TC-MONTHLY-STATS-001")
def test_get_monthly_summary_adds_period_and_returns_top_categories_sorted():
    StatsService = _load_stats_service_class()
    entry_repo = Mock()
    category_repo = Mock()
    service = StatsService(entry_repo=entry_repo, category_repo=category_repo)

    entry_repo.get_statistics.return_value = {
        "total_income": 100000.0,
        "total_expense": 34500.0,
        "balance": 65500.0,
        "entry_count": 20,
    }
    category_repo.get_all.return_value = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
        SimpleNamespace(id=3),
    ]
    category_repo.get_category_stats.side_effect = [
        {"category_name": "Продукты", "total": 15000.0},
        {"category_name": "Транспорт", "total": 7000.0},
        {"category_name": "Развлечения", "total": 12000.0},
    ]

    result = service.get_monthly_summary(2026, 3)

    entry_repo.get_statistics.assert_called_once_with(2026, 3)
    assert result["period"] == "2026.03"
    assert result["total_income"] == 100000.0
    assert result["total_expense"] == 34500.0
    assert result["balance"] == 65500.0
    assert [c["category_name"] for c in result["top_categories"]] == [
        "Продукты",
        "Развлечения",
        "Транспорт",
    ]
