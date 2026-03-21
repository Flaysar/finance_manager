# Traceability: Test Cases to Automation

## TC-ADD-ENTRY-001
- **Requirement**: Пользователь может добавить доход/расход с датой и категориями.
- **Manual scenario**: Добавление записи о расходе с выбором подкатегории.
- **Automated test**: `tests/test_entry_service.py::test_add_entry_creates_entry_with_selected_subcategories_and_formats_output`
- **Marker**: `@pytest.mark.testcase("TC-ADD-ENTRY-001")`
- **Run command**: `pytest -q -m testcase`

## TC-MONTHLY-STATS-001
- **Requirement**: Пользователь может просматривать сводную статистику за выбранный месяц.
- **Manual scenario**: Открытие статистики за месяц и просмотр топа категорий.
- **Automated test**: `tests/test_stats_service.py::test_get_monthly_summary_adds_period_and_returns_top_categories_sorted`
- **Marker**: `@pytest.mark.testcase("TC-MONTHLY-STATS-001")`
- **Run command**: `pytest -q -m testcase`

## TC-ADD-ENTRY-NEG-001
- **Requirement**: Система валидирует формат даты при добавлении записи.
- **Manual scenario**: Ввести дату в неверном формате и получить ошибку валидации.
- **Automated test**: `tests/test_entry_service.py::test_add_entry_raises_value_error_for_invalid_date_format`
- **Marker**: `@pytest.mark.testcase("TC-ADD-ENTRY-NEG-001")`
- **Run command**: `pytest -q -m testcase`

