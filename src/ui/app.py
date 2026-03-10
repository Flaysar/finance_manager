import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from src.services.entry_service import EntryService
from src.services.category_service import CategoryService
from src.services.stats_service import StatsService


class BudgetApp:
    def __init__(self, entry_service: EntryService, category_service: CategoryService, stats_service: StatsService):
        self.entry_service = entry_service
        self.category_service = category_service
        self.stats_service = stats_service

        self.root = tk.Tk()
        self.root.title("Budget App - Управление финансами")
        self.root.geometry("1000x700")

        self._setup_menu()
        self._setup_ui()
        self._load_data()

    def _setup_menu(self):
        """Создание меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Экспорт данных", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)

        # Меню Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)

    def _setup_ui(self):
        """Создание интерфейса"""
        # Верхняя панель с кнопками
        toolbar = tk.Frame(self.root, bg='#f0f0f0', height=50)
        toolbar.pack(fill=tk.X, padx=2, pady=2)

        tk.Button(toolbar, text="➕ Доход", command=lambda: self.add_entry('income'),
                  bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'),
                  padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(toolbar, text="➖ Расход", command=lambda: self.add_entry('expense'),
                  bg='#f44336', fg='white', font=('Arial', 10, 'bold'),
                  padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(toolbar, text="🔄 Обновить", command=self._load_data,
                  bg='#2196F3', fg='white', font=('Arial', 10, 'bold'),
                  padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(toolbar, text="📊 Статистика", command=self.show_statistics,
                  bg='#FF9800', fg='white', font=('Arial', 10, 'bold'),
                  padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(toolbar, text="⚙ Категории", command=self.manage_categories,
                  bg='#9C27B0', fg='white', font=('Arial', 10, 'bold'),
                  padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        # Основной контейнер
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Левая панель - статистика
        left_panel = tk.Frame(main_container, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        # Карточка баланса
        balance_frame = tk.LabelFrame(left_panel, text="Баланс", font=('Arial', 12, 'bold'))
        balance_frame.pack(fill=tk.X, pady=(0, 10))

        self.balance_label = tk.Label(balance_frame, text="0.00 ₽",
                                      font=('Arial', 20, 'bold'), fg='#2196F3')
        self.balance_label.pack(pady=10)

        # Доходы и расходы
        stats_frame = tk.Frame(left_panel)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        income_frame = tk.LabelFrame(stats_frame, text="Доходы", fg='#4CAF50')
        income_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.income_label = tk.Label(income_frame, text="0.00 ₽",
                                     font=('Arial', 12), fg='#4CAF50')
        self.income_label.pack(pady=5)

        expense_frame = tk.LabelFrame(stats_frame, text="Расходы", fg='#f44336')
        expense_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.expense_label = tk.Label(expense_frame, text="0.00 ₽",
                                      font=('Arial', 12), fg='#f44336')
        self.expense_label.pack(pady=5)

        # Правая панель - таблица записей
        right_panel = tk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Создаем таблицу
        columns = ('Дата', 'Название', 'Сумма', 'Тип', 'Категории')
        self.tree = ttk.Treeview(right_panel, columns=columns, show='headings', height=20)

        # Настраиваем колонки
        self.tree.heading('Дата', text='Дата')
        self.tree.heading('Название', text='Название')
        self.tree.heading('Сумма', text='Сумма')
        self.tree.heading('Тип', text='Тип')
        self.tree.heading('Категории', text='Категории')

        self.tree.column('Дата', width=100)
        self.tree.column('Название', width=250)
        self.tree.column('Сумма', width=100)
        self.tree.column('Тип', width=80)
        self.tree.column('Категории', width=200)

        # Добавляем скроллбар
        scrollbar = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Контекстное меню для таблицы
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Удалить запись", command=self.delete_selected)
        self.context_menu.add_command(label="Редактировать категории", command=self.edit_categories)

        self.tree.bind("<Button-3>", self.show_context_menu)

    def _load_data(self):
        """Загрузка данных"""
        try:
            # Загружаем статистику
            today = datetime.now()
            stats = self.stats_service.get_monthly_summary(today.year, today.month)

            self.balance_label.config(text=f"{stats['balance']:.2f} ₽")
            self.income_label.config(text=f"{stats['total_income']:.2f} ₽")
            self.expense_label.config(text=f"{stats['total_expense']:.2f} ₽")

            # Загружаем последние записи
            entries = self.entry_service.get_recent_entries(50)

            # Очищаем таблицу
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Заполняем таблицу
            for entry in entries:
                categories_str = ', '.join([s['name'] for s in entry['subcategories']])
                self.tree.insert('', 'end', values=(
                    entry['date'],
                    entry['name'],
                    f"{entry['price']:.2f} ₽",
                    'Доход' if entry['type'] == 'income' else 'Расход',
                    categories_str
                ), tags=(entry['id'],))

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные: {str(e)}")

    def add_entry(self, entry_type):
        """Диалог добавления записи"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Добавление {'дохода' if entry_type == 'income' else 'расхода'}")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Поля ввода
        tk.Label(dialog, text="Название:", font=('Arial', 11)).pack(pady=5)
        name_entry = tk.Entry(dialog, font=('Arial', 11), width=40)
        name_entry.pack(pady=5)

        tk.Label(dialog, text="Сумма:", font=('Arial', 11)).pack(pady=5)
        price_entry = tk.Entry(dialog, font=('Arial', 11), width=40)
        price_entry.pack(pady=5)

        tk.Label(dialog, text="Дата (ГГГГ-ММ-ДД):", font=('Arial', 11)).pack(pady=5)
        date_entry = tk.Entry(dialog, font=('Arial', 11), width=40)
        date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        date_entry.pack(pady=5)

        tk.Label(dialog, text="Категории:", font=('Arial', 11)).pack(pady=5)

        # Получаем категории для выбора
        categories = self.category_service.get_all_categories()

        # Создаем фрейм со скроллом для выбора подкатегорий
        categories_frame = tk.Frame(dialog)
        categories_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(categories_frame)
        scrollbar = tk.Scrollbar(categories_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Словарь для хранения переменных выбора
        self.subcategory_vars = {}

        # Добавляем категории и подкатегории
        for category in categories:
            # Заголовок категории
            cat_label = tk.Label(scrollable_frame, text=category['name'],
                                 font=('Arial', 10, 'bold'), fg=category.get('color', '#000000'))
            cat_label.pack(anchor='w', pady=(5, 0))

            # Подкатегории
            for subcat in category['subcategories']:
                var = tk.BooleanVar()
                cb = tk.Checkbutton(scrollable_frame, text=subcat['name'],
                                    variable=var, anchor='w')
                cb.pack(anchor='w', padx=(20, 0))
                self.subcategory_vars[subcat['id']] = var

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def save():
            try:
                name = name_entry.get().strip()
                if not name:
                    messagebox.showerror("Ошибка", "Введите название")
                    return

                price = float(price_entry.get())
                if price <= 0:
                    messagebox.showerror("Ошибка", "Сумма должна быть положительной")
                    return

                date_str = date_entry.get().strip()

                # Собираем выбранные подкатегории
                selected_subcategories = [
                    subcat_id for subcat_id, var in self.subcategory_vars.items()
                    if var.get()
                ]

                self.entry_service.add_entry(
                    name=name,
                    price=price,
                    type=entry_type,
                    subcategory_ids=selected_subcategories,
                    date=date_str
                )

                dialog.destroy()
                self._load_data()
                messagebox.showinfo("Успех", "Запись добавлена")

            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректную сумму")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {str(e)}")

        tk.Button(dialog, text="Сохранить", command=save,
                  bg='#4CAF50', fg='white', font=('Arial', 11, 'bold'),
                  padx=20, pady=5).pack(pady=20)

    def show_context_menu(self, event):
        """Показать контекстное меню"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def delete_selected(self):
        """Удалить выбранную запись"""
        selected = self.tree.selection()
        if not selected:
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранную запись?"):
            item = selected[0]
            entry_id = self.tree.item(item, "tags")[0]

            if self.entry_service.delete_entry(entry_id):
                self._load_data()
                messagebox.showinfo("Успех", "Запись удалена")

    def edit_categories(self):
        """Редактировать категории записи"""
        selected = self.tree.selection()
        if not selected:
            return

        item = selected[0]
        entry_id = self.tree.item(item, "tags")[0]

        # Получаем запись
        entries = self.entry_service.get_recent_entries(100)
        entry = next((e for e in entries if e['id'] == entry_id), None)

        if entry:
            self.show_edit_categories_dialog(entry)

    def show_edit_categories_dialog(self, entry):
        """Диалог редактирования категорий записи"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Редактирование категорий")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text=f"Запись: {entry['name']}",
                 font=('Arial', 12, 'bold')).pack(pady=10)

        # Фрейм с категориями
        categories_frame = tk.Frame(dialog)
        categories_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(categories_frame)
        scrollbar = tk.Scrollbar(categories_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Получаем все категории
        categories = self.category_service.get_all_categories()

        # Словарь для хранения переменных
        vars_dict = {}

        # Текущие подкатегории записи
        current_subcat_ids = [s['id'] for s in entry['subcategories']]

        for category in categories:
            cat_label = tk.Label(scrollable_frame, text=category['name'],
                                 font=('Arial', 10, 'bold'))
            cat_label.pack(anchor='w', pady=(5, 0))

            for subcat in category['subcategories']:
                var = tk.BooleanVar(value=subcat['id'] in current_subcat_ids)
                cb = tk.Checkbutton(scrollable_frame, text=subcat['name'],
                                    variable=var, anchor='w')
                cb.pack(anchor='w', padx=(20, 0))
                vars_dict[subcat['id']] = var

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def save():
            # Удаляем все текущие связи
            for subcat_id in current_subcat_ids:
                self.entry_service.remove_subcategory_from_entry(entry['id'], subcat_id)

            # Добавляем новые
            for subcat_id, var in vars_dict.items():
                if var.get():
                    self.entry_service.add_subcategory_to_entry(entry['id'], subcat_id)

            dialog.destroy()
            self._load_data()
            messagebox.showinfo("Успех", "Категории обновлены")

        tk.Button(dialog, text="Сохранить", command=save,
                  bg='#4CAF50', fg='white', font=('Arial', 11, 'bold'),
                  padx=20, pady=5).pack(pady=10)

    def show_statistics(self):
        """Показать окно статистики"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Статистика")
        dialog.geometry("600x500")
        dialog.transient(self.root)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка с текущим месяцем
        current_month_frame = tk.Frame(notebook)
        notebook.add(current_month_frame, text="Текущий месяц")

        today = datetime.now()
        stats = self.stats_service.get_monthly_summary(today.year, today.month)

        # Отображаем статистику
        stats_text = tk.Text(current_month_frame, font=('Arial', 11), wrap=tk.WORD)
        stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        stats_text.insert(tk.END, f"Период: {stats['period']}\n\n")
        stats_text.insert(tk.END, f"Доходы: {stats['total_income']:.2f} ₽\n")
        stats_text.insert(tk.END, f"Расходы: {stats['total_expense']:.2f} ₽\n")
        stats_text.insert(tk.END, f"Баланс: {stats['balance']:.2f} ₽\n")
        stats_text.insert(tk.END, f"Количество записей: {stats['entry_count']}\n\n")

        if stats.get('top_categories'):
            stats_text.insert(tk.END, "Топ категорий:\n")
            for cat in stats['top_categories']:
                stats_text.insert(tk.END, f"  {cat['category_name']}: {cat['total']:.2f} ₽\n")

        stats_text.config(state=tk.DISABLED)

        # Вкладка с выбором периода
        period_frame = tk.Frame(notebook)
        notebook.add(period_frame, text="Выбор периода")

        tk.Label(period_frame, text="Год:", font=('Arial', 11)).pack(pady=5)
        year_entry = tk.Entry(period_frame, font=('Arial', 11))
        year_entry.insert(0, str(today.year))
        year_entry.pack(pady=5)

        tk.Label(period_frame, text="Месяц (1-12):", font=('Arial', 11)).pack(pady=5)
        month_entry = tk.Entry(period_frame, font=('Arial', 11))
        month_entry.insert(0, str(today.month))
        month_entry.pack(pady=5)

        result_text = tk.Text(period_frame, font=('Arial', 11), wrap=tk.WORD, height=15)
        result_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def show_period_stats():
            try:
                year = int(year_entry.get())
                month = int(month_entry.get())

                stats = self.stats_service.get_monthly_summary(year, month)

                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, f"Период: {year}.{month:02d}\n\n")
                result_text.insert(tk.END, f"Доходы: {stats['total_income']:.2f} ₽\n")
                result_text.insert(tk.END, f"Расходы: {stats['total_expense']:.2f} ₽\n")
                result_text.insert(tk.END, f"Баланс: {stats['balance']:.2f} ₽\n")
                result_text.insert(tk.END, f"Количество записей: {stats['entry_count']}\n")

            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректные значения")

        tk.Button(period_frame, text="Показать", command=show_period_stats,
                  bg='#2196F3', fg='white', font=('Arial', 11),
                  padx=20, pady=5).pack(pady=5)

    def manage_categories(self):
        """Управление категориями"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Управление категориями")
        dialog.geometry("600x500")
        dialog.transient(self.root)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка с категориями
        categories_frame = tk.Frame(notebook)
        notebook.add(categories_frame, text="Категории")

        # Список категорий
        categories_list = tk.Listbox(categories_frame, font=('Arial', 11))
        categories_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Загружаем категории
        categories = self.category_service.get_all_categories()
        for cat in categories:
            categories_list.insert(tk.END, f"{cat['name']} ({cat['type']})")

        # Кнопки для управления категориями
        btn_frame = tk.Frame(categories_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(btn_frame, text="Добавить категорию",
                  command=lambda: self.add_category_dialog(dialog),
                  bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=5)

        # Вкладка с подкатегориями
        subcategories_frame = tk.Frame(notebook)
        notebook.add(subcategories_frame, text="Подкатегории")

        # Выбор категории
        tk.Label(subcategories_frame, text="Категория:", font=('Arial', 11)).pack(pady=5)

        category_var = tk.StringVar()
        category_combo = ttk.Combobox(subcategories_frame, textvariable=category_var,
                                      values=[f"{c['name']}" for c in categories],
                                      font=('Arial', 11), width=40)
        category_combo.pack(pady=5)

        # Список подкатегорий
        subcategories_list = tk.Listbox(subcategories_frame, font=('Arial', 11))
        subcategories_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def update_subcategories(*args):
            subcategories_list.delete(0, tk.END)
            selected_cat = category_var.get()
            if selected_cat:
                cat = next((c for c in categories if c['name'] == selected_cat), None)
                if cat:
                    for subcat in cat['subcategories']:
                        subcategories_list.insert(tk.END, subcat['name'])

        category_var.trace('w', update_subcategories)

        # Кнопка добавления подкатегории
        tk.Button(subcategories_frame, text="Добавить подкатегорию",
                  command=lambda: self.add_subcategory_dialog(dialog, category_var.get()),
                  bg='#4CAF50', fg='white').pack(pady=5)

    def add_category_dialog(self, parent):
        """Диалог добавления категории"""
        dialog = tk.Toplevel(parent)
        dialog.title("Добавить категорию")
        dialog.geometry("300x200")
        dialog.transient(parent)
        dialog.grab_set()

        tk.Label(dialog, text="Название:", font=('Arial', 11)).pack(pady=5)
        name_entry = tk.Entry(dialog, font=('Arial', 11), width=30)
        name_entry.pack(pady=5)

        tk.Label(dialog, text="Тип:", font=('Arial', 11)).pack(pady=5)
        type_var = tk.StringVar(value="expense")
        ttk.Radiobutton(dialog, text="Расход", variable=type_var,
                        value="expense").pack()
        ttk.Radiobutton(dialog, text="Доход", variable=type_var,
                        value="income").pack()

        def save():
            name = name_entry.get().strip()
            if name:
                self.category_service.create_category(name, type_var.get())
                dialog.destroy()
                messagebox.showinfo("Успех", "Категория добавлена")

        tk.Button(dialog, text="Сохранить", command=save,
                  bg='#4CAF50', fg='white', font=('Arial', 11),
                  padx=20, pady=5).pack(pady=20)

    def add_subcategory_dialog(self, parent, category_name):
        """Диалог добавления подкатегории"""
        if not category_name:
            messagebox.showerror("Ошибка", "Выберите категорию")
            return

        dialog = tk.Toplevel(parent)
        dialog.title("Добавить подкатегорию")
        dialog.geometry("300x150")
        dialog.transient(parent)
        dialog.grab_set()

        tk.Label(dialog, text=f"Категория: {category_name}",
                 font=('Arial', 11)).pack(pady=5)

        tk.Label(dialog, text="Название:", font=('Arial', 11)).pack(pady=5)
        name_entry = tk.Entry(dialog, font=('Arial', 11), width=30)
        name_entry.pack(pady=5)

        def save():
            name = name_entry.get().strip()
            if name:
                # Получаем ID категории
                categories = self.category_service.get_all_categories()
                category = next((c for c in categories if c['name'] == category_name), None)
                if category:
                    self.category_service.create_subcategory(name, category['id'])
                    dialog.destroy()
                    messagebox.showinfo("Успех", "Подкатегория добавлена")

        tk.Button(dialog, text="Сохранить", command=save,
                  bg='#4CAF50', fg='white', font=('Arial', 11),
                  padx=20, pady=5).pack(pady=20)

    def export_data(self):
        """Экспорт данных (заглушка)"""
        messagebox.showinfo("Информация", "Функция экспорта будет добавлена позже")

    def show_about(self):
        """О программе"""
        messagebox.showinfo("О программе",
                            "Budget App\nВерсия 1.0\n\n"
                            "Приложение для учета финансов\n"
                            "с поддержкой категорий и подкатегорий")

    def run(self):
        """Запуск приложения"""
        self.root.mainloop()