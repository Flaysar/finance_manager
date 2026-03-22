import platform
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
from calendar import monthrange
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from src.services.entry_service import EntryService
from src.services.category_service import CategoryService
from src.services.stats_service import StatsService


# Единая светлая тема (Nord-inspired)
THEME = {
    "bg": "#eceff4",
    "panel": "#ffffff",
    "sidebar": "#e5e9f0",
    "text": "#2e3440",
    "muted": "#4c566a",
    "accent": "#5e81ac",
    "accent_hover": "#81a1c1",
    "income": "#a3be8c",
    "expense": "#bf616a",
    "balance": "#88c0d0",
    "border": "#d8dee9",
    "tree_alt": "#f8f9fb",
    "error": "#bf616a",
}


def _base_font_family():
    if platform.system() == "Windows":
        return "Segoe UI"
    return "Arial"


class BudgetApp:
    def __init__(self, entry_service: EntryService, category_service: CategoryService, stats_service: StatsService):
        self.entry_service = entry_service
        self.category_service = category_service
        self.stats_service = stats_service

        self._font_scale = "normal"  # small | normal | large
        self._base_sizes = {"small": 9, "normal": 10, "large": 12}
        self._sort_column = "date"
        self._sort_reverse = False
        self._raw_entries = []
        self._entries_by_id = {}
        self._last_load_ok = True
        self._last_error_msg = ""

        # Сначала корневое окно — иначе StringVar/trace вызовут "no default root window"
        self.root = tk.Tk()
        self.root.title("Budget App — учёт финансов")
        self.root.geometry("1100x720")
        self.root.minsize(900, 560)
        self.root.configure(bg=THEME["bg"])

        self._filter_mode = tk.StringVar(master=self.root, value="all")
        self._search_var = tk.StringVar(master=self.root)
        self._search_var.trace_add("write", lambda *a: self._refresh_table())

        self._fonts = {}
        self._setup_styles()
        self._setup_menu()
        self._setup_ui()
        self._load_data()

        self.root.bind_all("<F5>", lambda e: self._load_data())

    def _setup_styles(self):
        self._apply_font_sizes()
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "TNotebook",
            background=THEME["bg"],
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            padding=[12, 6],
            font=self._fonts["ui"],
        )
        style.configure(
            "Treeview",
            background=THEME["panel"],
            fieldbackground=THEME["panel"],
            foreground=THEME["text"],
            rowheight=26,
            font=self._fonts["ui"],
        )
        style.configure(
            "Treeview.Heading",
            font=self._fonts["heading_small"],
        )
        style.map(
            "Treeview",
            background=[("selected", THEME["accent"])],
            foreground=[("selected", "#ffffff")],
        )

    def _apply_font_sizes(self):
        ff = _base_font_family()
        b = self._base_sizes[self._font_scale]
        self._fonts = {
            "title": (ff, b + 4, "bold"),
            "heading": (ff, b + 2, "bold"),
            "heading_small": (ff, b, "bold"),
            "ui": (ff, b),
            "stat_big": (ff, b + 8, "bold"),
            "stat": (ff, b + 1),
            "small": (ff, max(8, b - 1)),
        }

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Экспорт данных", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Шрифт: мелкий", command=lambda: self._set_font_scale("small"))
        view_menu.add_command(label="Шрифт: обычный", command=lambda: self._set_font_scale("normal"))
        view_menu.add_command(label="Шрифт: крупный", command=lambda: self._set_font_scale("large"))

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)

    def _set_font_scale(self, scale: str):
        self._font_scale = scale
        self._apply_font_sizes()
        self._setup_styles()
        self._apply_fonts_to_widgets()
        self._refresh_table()

    def _apply_fonts_to_widgets(self):
        if hasattr(self, "balance_label"):
            self.balance_label.config(font=self._fonts["stat_big"])
        if hasattr(self, "income_label"):
            self.income_label.config(font=self._fonts["stat"])
        if hasattr(self, "expense_label"):
            self.expense_label.config(font=self._fonts["stat"])
        if hasattr(self, "status_label"):
            self.status_label.config(font=self._fonts["small"])

    def _setup_ui(self):
        outer = tk.Frame(self.root, bg=THEME["bg"])
        outer.pack(fill=tk.BOTH, expand=True)

        # Боковая панель (п. 13)
        sidebar = tk.Frame(outer, bg=THEME["sidebar"], width=200, highlightthickness=1, highlightbackground=THEME["border"])
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="Budget App",
            bg=THEME["sidebar"],
            fg=THEME["text"],
            font=self._fonts["heading"],
        ).pack(pady=(16, 8), padx=12, anchor="w")

        tk.Label(
            sidebar,
            text="Быстрые действия",
            bg=THEME["sidebar"],
            fg=THEME["muted"],
            font=self._fonts["small"],
        ).pack(padx=12, anchor="w")

        def sb_btn(text, cmd, bg):
            b = tk.Button(
                sidebar,
                text=text,
                command=cmd,
                bg=bg,
                fg="#ffffff",
                activebackground=THEME["accent_hover"],
                activeforeground="#ffffff",
                font=self._fonts["ui"],
                relief=tk.FLAT,
                padx=12,
                pady=8,
                cursor="hand2",
            )
            b.pack(fill=tk.X, padx=10, pady=4)
            return b

        sb_btn("Доход", lambda: self.add_entry("income"), THEME["income"])
        sb_btn("Расход", lambda: self.add_entry("expense"), THEME["expense"])
        sb_btn("Обновить данные", self._load_data, THEME["accent"])

        # Основная область: вкладки (п. 12)
        main = tk.Frame(outer, bg=THEME["bg"])
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8), pady=8)

        self.main_notebook = ttk.Notebook(main)
        self.main_notebook.pack(fill=tk.BOTH, expand=True)

        tab_ops = tk.Frame(self.main_notebook, bg=THEME["bg"])
        tab_stats = tk.Frame(self.main_notebook, bg=THEME["bg"])
        tab_cat = tk.Frame(self.main_notebook, bg=THEME["bg"])

        self.main_notebook.add(tab_ops, text="  Операции  ")
        self.main_notebook.add(tab_stats, text="  Статистика  ")
        self.main_notebook.add(tab_cat, text="  Категории  ")

        self._build_operations_tab(tab_ops)
        self._build_statistics_tab(tab_stats)
        self._build_categories_tab(tab_cat)

        # Статусная строка (п. 8)
        status_frame = tk.Frame(self.root, bg=THEME["border"], height=24)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = tk.Label(
            status_frame,
            text="Готово",
            bg=THEME["border"],
            fg=THEME["text"],
            font=self._fonts["small"],
            anchor="w",
            padx=8,
            pady=3,
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_operations_tab(self, parent):
        parent.configure(bg=THEME["bg"])

        # Фильтры и поиск (п. 5, 6)
        filt = tk.Frame(parent, bg=THEME["panel"], highlightthickness=1, highlightbackground=THEME["border"])
        filt.pack(fill=tk.X, pady=(0, 8), padx=0)

        inner = tk.Frame(filt, bg=THEME["panel"])
        inner.pack(fill=tk.X, padx=12, pady=10)

        tk.Label(inner, text="Показать:", bg=THEME["panel"], fg=THEME["text"], font=self._fonts["ui"]).pack(side=tk.LEFT)

        modes = [
            ("all", "Все"),
            ("income", "Только доходы"),
            ("expense", "Только расходы"),
            ("month", "Текущий месяц"),
        ]
        for val, lbl in modes:
            ttk.Radiobutton(
                inner,
                text=lbl,
                variable=self._filter_mode,
                value=val,
                command=self._on_filter_changed,
            ).pack(side=tk.LEFT, padx=(10, 0))

        tk.Label(inner, text="Поиск:", bg=THEME["panel"], fg=THEME["text"], font=self._fonts["ui"]).pack(side=tk.LEFT, padx=(24, 0))
        search_e = ttk.Entry(inner, textvariable=self._search_var, width=28)
        search_e.pack(side=tk.LEFT, padx=(6, 0))

        body = tk.Frame(parent, bg=THEME["bg"])
        body.pack(fill=tk.BOTH, expand=True)

        # Карточки статистики (п. 2)
        left_panel = tk.Frame(body, bg=THEME["bg"], width=260)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        balance_frame = tk.LabelFrame(
            left_panel,
            text=" Баланс (текущий месяц) ",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=self._fonts["heading_small"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
            labelanchor="nw",
        )
        balance_frame.pack(fill=tk.X, pady=(0, 10))
        self.balance_label = tk.Label(
            balance_frame,
            text="0.00 ₽",
            bg=THEME["panel"],
            fg=THEME["balance"],
            font=self._fonts["stat_big"],
        )
        self.balance_label.pack(pady=(12, 16), padx=12, anchor="center")

        stats_row = tk.Frame(left_panel, bg=THEME["bg"])
        stats_row.pack(fill=tk.X)

        income_frame = tk.LabelFrame(
            stats_row,
            text=" Доходы ",
            bg=THEME["panel"],
            fg=THEME["income"],
            font=self._fonts["small"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
        )
        income_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self.income_label = tk.Label(
            income_frame,
            text="0.00 ₽",
            bg=THEME["panel"],
            fg=THEME["income"],
            font=self._fonts["stat"],
        )
        self.income_label.pack(pady=10, padx=8)

        expense_frame = tk.LabelFrame(
            stats_row,
            text=" Расходы ",
            bg=THEME["panel"],
            fg=THEME["expense"],
            font=self._fonts["small"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
        )
        expense_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.expense_label = tk.Label(
            expense_frame,
            text="0.00 ₽",
            bg=THEME["panel"],
            fg=THEME["expense"],
            font=self._fonts["stat"],
        )
        self.expense_label.pack(pady=10, padx=8)

        # Таблица (п. 4, 7)
        right_panel = tk.Frame(body, bg=THEME["bg"])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        cols = ("date", "name", "amount", "type", "cats")
        self.tree = ttk.Treeview(right_panel, columns=cols, show="headings", height=22, selectmode="browse")

        headings = {
            "date": "Дата",
            "name": "Название",
            "amount": "Сумма",
            "type": "Тип",
            "cats": "Категории",
        }
        widths = {"date": 100, "name": 240, "amount": 110, "type": 90, "cats": 220}
        for c in cols:
            self.tree.heading(
                c,
                text=headings[c],
                command=lambda col=c: self._on_column_sort(col),
            )
            anchor = "e" if c == "amount" else "w"
            self.tree.column(c, width=widths[c], anchor=anchor, minwidth=60, stretch=True)

        scroll = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("odd", background=THEME["panel"])
        self.tree.tag_configure("even", background=THEME["tree_alt"])

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Редактировать запись", command=self.edit_entry)
        self.context_menu.add_command(label="Удалить запись", command=self.delete_selected)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def _on_filter_changed(self):
        self._load_data()

    def _build_statistics_tab(self, parent):
        parent.configure(bg=THEME["bg"])
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Вкладка "Текущий месяц"
        current_month_frame = tk.Frame(notebook, bg=THEME["bg"])
        notebook.add(current_month_frame, text="Текущий месяц")
        
        # Верхняя панель с текстовой информацией
        info_frame = tk.Frame(current_month_frame, bg=THEME["panel"], highlightthickness=1, highlightbackground=THEME["border"])
        info_frame.pack(fill=tk.X, padx=8, pady=(8, 0))
        
        self.stats_text_current = tk.Text(
            info_frame,
            font=self._fonts["ui"],
            wrap=tk.WORD,
            bg=THEME["panel"],
            fg=THEME["text"],
            relief=tk.FLAT,
            padx=12,
            pady=12,
            height=8,
        )
        self.stats_text_current.pack(fill=tk.BOTH, padx=8, pady=8)

        # Контейнер для графиков
        charts_frame = tk.Frame(current_month_frame, bg=THEME["bg"])
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        self.stats_canvas_current = tk.Canvas(charts_frame, bg=THEME["bg"], highlightthickness=0)
        self.stats_canvas_current.pack(fill=tk.BOTH, expand=True)
        self.current_month_charts = None

        # Вкладка "Выбор периода"
        period_frame = tk.Frame(notebook, bg=THEME["bg"])
        notebook.add(period_frame, text="Выбор периода")

        today = datetime.now()
        pf = tk.Frame(period_frame, bg=THEME["bg"])
        pf.pack(fill=tk.X, padx=12, pady=8)

        tk.Label(pf, text="Год:", bg=THEME["bg"], font=self._fonts["ui"]).pack(side=tk.LEFT)
        self.stats_year = tk.Entry(pf, width=8, font=self._fonts["ui"])
        self.stats_year.insert(0, str(today.year))
        self.stats_year.pack(side=tk.LEFT, padx=6)

        tk.Label(pf, text="Месяц (1–12):", bg=THEME["bg"], font=self._fonts["ui"]).pack(side=tk.LEFT, padx=(16, 0))
        self.stats_month = tk.Entry(pf, width=6, font=self._fonts["ui"])
        self.stats_month.insert(0, str(today.month))
        self.stats_month.pack(side=tk.LEFT, padx=6)

        tk.Button(
            pf,
            text="Показать",
            command=self._show_period_stats_embedded,
            bg=THEME["accent"],
            fg="#ffffff",
            font=self._fonts["ui"],
            relief=tk.FLAT,
            padx=14,
            pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=12)

        # Верхняя панель с текстовой информацией за период
        info_period_frame = tk.Frame(period_frame, bg=THEME["panel"], highlightthickness=1, highlightbackground=THEME["border"])
        info_period_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        
        self.stats_text_period = tk.Text(
            info_period_frame,
            font=self._fonts["ui"],
            wrap=tk.WORD,
            height=8,
            bg=THEME["panel"],
            fg=THEME["text"],
            relief=tk.FLAT,
            padx=12,
            pady=12,
        )
        self.stats_text_period.pack(fill=tk.BOTH, padx=8, pady=8)

        # Контейнер для графиков периода
        period_charts_frame = tk.Frame(period_frame, bg=THEME["bg"])
        period_charts_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        self.stats_canvas_period = tk.Canvas(period_charts_frame, bg=THEME["bg"], highlightthickness=0)
        self.stats_canvas_period.pack(fill=tk.BOTH, expand=True)
        self.period_charts = None

        self.main_notebook.bind("<<NotebookTabChanged>>", self._on_main_tab_changed)

    def _on_main_tab_changed(self, event=None):
        try:
            idx = self.main_notebook.index(self.main_notebook.select())
            if idx == 1:
                self._refresh_statistics_current_tab()
        except tk.TclError:
            pass

    def _refresh_statistics_current_tab(self):
        today = datetime.now()
        try:
            stats = self.stats_service.get_monthly_summary(today.year, today.month)
            expenses_by_cat = self.stats_service.get_expenses_by_category(today.year, today.month)
            income_by_cat = self.stats_service.get_income_by_category(today.year, today.month)
            
            # Обновляем текстовую информацию
            t = self.stats_text_current
            t.config(state=tk.NORMAL)
            t.delete(1.0, tk.END)
            t.insert(tk.END, f"Период: {stats['period']}\n")
            t.insert(tk.END, f"Доходы: {stats['total_income']:.2f} ₽  |  ")
            t.insert(tk.END, f"Расходы: {stats['total_expense']:.2f} ₽  |  ")
            t.insert(tk.END, f"Баланс: {stats['balance']:.2f} ₽  |  ")
            t.insert(tk.END, f"Записей: {stats['entry_count']}")
            t.config(state=tk.DISABLED)
            
            # Рисуем графики
            self._draw_pie_charts(self.stats_canvas_current, expenses_by_cat, income_by_cat)
            
        except Exception as e:
            self.stats_text_current.config(state=tk.NORMAL)
            self.stats_text_current.delete(1.0, tk.END)
            self.stats_text_current.insert(tk.END, f"Ошибка загрузки: {e}")
            self.stats_text_current.config(state=tk.DISABLED)

    def _show_period_stats_embedded(self):
        try:
            year = int(self.stats_year.get())
            month = int(self.stats_month.get())
            stats = self.stats_service.get_monthly_summary(year, month)
            expenses_by_cat = self.stats_service.get_expenses_by_category(year, month)
            income_by_cat = self.stats_service.get_income_by_category(year, month)
            
            # Обновляем текстовую информацию
            self.stats_text_period.config(state=tk.NORMAL)
            self.stats_text_period.delete(1.0, tk.END)
            self.stats_text_period.insert(tk.END, f"Период: {year}.{month:02d}\n")
            self.stats_text_period.insert(tk.END, f"Доходы: {stats['total_income']:.2f} ₽  |  ")
            self.stats_text_period.insert(tk.END, f"Расходы: {stats['total_expense']:.2f} ₽  |  ")
            self.stats_text_period.insert(tk.END, f"Баланс: {stats['balance']:.2f} ₽  |  ")
            self.stats_text_period.insert(tk.END, f"Записей: {stats['entry_count']}")
            self.stats_text_period.config(state=tk.DISABLED)
            
            # Рисуем графики
            self._draw_pie_charts(self.stats_canvas_period, expenses_by_cat, income_by_cat)
            
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные год и месяц")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _draw_pie_charts(self, canvas, expenses_dict: dict, income_dict: dict):
        """Рисует два pie chart для расходов и доходов"""
        # Очищаем старые графики
        for widget in canvas.winfo_children():
            widget.destroy()
        
        fig = Figure(figsize=(12, 4.5), dpi=100, facecolor='#ffffff')
        
        # Граф расходов (слева)
        ax1 = fig.add_subplot(121)
        if expenses_dict:
            # Используем контрастную палитру YlOrRd (желтый → оранжевый → красный)
            colors_exp = plt.cm.YlOrRd([(i + 0.3) / len(expenses_dict) for i in range(len(expenses_dict))])
            wedges, texts, autotexts = ax1.pie(
                expenses_dict.values(),
                labels=expenses_dict.keys(),
                autopct='%1.1f%%',
                colors=colors_exp,
                startangle=90,
                wedgeprops={'edgecolor': 'white', 'linewidth': 2.5},
                textprops={'fontsize': 9}
            )
            ax1.set_title('Расходы', fontsize=12, fontweight='bold', color='#000000', pad=10)
            # Улучшаем видимость текста
            for text in texts:
                text.set_color('#000000')
                text.set_fontsize(9)
                text.set_fontweight('bold')
            for autotext in autotexts:
                autotext.set_color('#000000')
                autotext.set_fontsize(9)
                autotext.set_fontweight('bold')
        else:
            ax1.text(0.5, 0.5, 'Нет данных', ha='center', va='center', 
                    fontsize=12, color='#999999')
            ax1.set_title('Расходы', fontsize=12, fontweight='bold', color='#000000')
            ax1.set_xticks([])
            ax1.set_yticks([])
        
        # Граф доходов (справа)
        ax2 = fig.add_subplot(122)
        if income_dict:
            # Используем контрастную палитру YlGn (желтый → зеленый)
            colors_inc = plt.cm.YlGn([(i + 0.3) / len(income_dict) for i in range(len(income_dict))])
            wedges, texts, autotexts = ax2.pie(
                income_dict.values(),
                labels=income_dict.keys(),
                autopct='%1.1f%%',
                colors=colors_inc,
                startangle=90,
                wedgeprops={'edgecolor': 'white', 'linewidth': 2.5},
                textprops={'fontsize': 9}
            )
            ax2.set_title('Доходы', fontsize=12, fontweight='bold', color='#000000', pad=10)
            # Улучшаем видимость текста
            for text in texts:
                text.set_color('#000000')
                text.set_fontsize(9)
                text.set_fontweight('bold')
            for autotext in autotexts:
                autotext.set_color('#000000')
                autotext.set_fontsize(9)
                autotext.set_fontweight('bold')
        else:
            ax2.text(0.5, 0.5, 'Нет данных', ha='center', va='center', 
                    fontsize=12, color='#999999')
            ax2.set_title('Доходы', fontsize=12, fontweight='bold', color='#000000')
            ax2.set_xticks([])
            ax2.set_yticks([])
        
        fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
        
        # Встраиваем график в Tkinter
        chart = FigureCanvasTkAgg(fig, master=canvas)
        chart.draw()
        chart.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_categories_tab(self, parent):
        parent.configure(bg=THEME["bg"])
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        categories_frame = tk.Frame(notebook, bg=THEME["bg"])
        notebook.add(categories_frame, text="Список категорий")

        categories_list = tk.Listbox(
            categories_frame,
            font=self._fonts["ui"],
            bg=THEME["panel"],
            fg=THEME["text"],
            selectbackground=THEME["accent"],
            height=16,
        )
        categories_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(categories_frame, bg=THEME["bg"])
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        subcategories_frame = tk.Frame(notebook, bg=THEME["bg"])
        notebook.add(subcategories_frame, text="Подкатегории")

        tk.Label(subcategories_frame, text="Категория:", bg=THEME["bg"], font=self._fonts["ui"]).pack(pady=(8, 4))

        category_var = tk.StringVar()
        category_combo = ttk.Combobox(subcategories_frame, textvariable=category_var, values=[], width=42)
        category_combo.pack(pady=4)

        subcategories_list = tk.Listbox(
            subcategories_frame,
            font=self._fonts["ui"],
            bg=THEME["panel"],
            fg=THEME["text"],
            selectbackground=THEME["accent"],
            height=14,
        )
        subcategories_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        categories = []

        def refresh_categories_in_dialog():
            nonlocal categories
            categories = self.category_service.get_all_categories()
            categories_list.delete(0, tk.END)
            for cat in categories:
                categories_list.insert(tk.END, f"{cat['name']} ({cat['type']})")
            names = [c["name"] for c in categories]
            category_combo["values"] = names
            current = category_var.get()
            if current and current not in names:
                category_var.set("")
            update_subcategories()

        def update_subcategories(*args):
            subcategories_list.delete(0, tk.END)
            selected_cat = category_var.get()
            if selected_cat:
                cat = next((c for c in categories if c["name"] == selected_cat), None)
                if cat:
                    for subcat in cat["subcategories"]:
                        subcategories_list.insert(tk.END, subcat["name"])

        def on_category_context_menu(event):
            selection = categories_list.curselection()
            if not selection:
                return
            idx = selection[0]
            cat = categories[idx]
            
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(
                label="Редактировать",
                command=lambda: self.edit_category_dialog(parent, cat, on_category_added=refresh_categories_in_dialog)
            )
            context_menu.add_command(
                label="Удалить",
                command=lambda: self.delete_category_with_confirm(cat["id"], refresh_categories_in_dialog)
            )
            context_menu.post(event.x_root, event.y_root)

        def on_subcategory_context_menu(event):
            selection = subcategories_list.curselection()
            if not selection:
                return
            idx = selection[0]
            selected_cat = category_var.get()
            if not selected_cat:
                return
            cat = next((c for c in categories if c["name"] == selected_cat), None)
            if not cat:
                return
            subcat = cat["subcategories"][idx]
            
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(
                label="Редактировать",
                command=lambda: self.edit_subcategory_dialog(parent, subcat, selected_cat, on_subcategory_added=refresh_categories_in_dialog)
            )
            context_menu.add_command(
                label="Удалить",
                command=lambda: self.delete_subcategory_with_confirm(subcat["id"], refresh_categories_in_dialog)
            )
            context_menu.post(event.x_root, event.y_root)

        categories_list.bind("<Button-3>", on_category_context_menu)
        subcategories_list.bind("<Button-3>", on_subcategory_context_menu)

        category_var.trace_add("write", update_subcategories)
        refresh_categories_in_dialog()

        tk.Button(
            btn_frame,
            text="Добавить категорию",
            command=lambda: self.add_category_dialog(parent, on_category_added=refresh_categories_in_dialog),
            bg=THEME["accent"],
            fg="#ffffff",
            font=self._fonts["ui"],
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.LEFT)

        tk.Button(
            subcategories_frame,
            text="Добавить подкатегорию",
            command=lambda: self.add_subcategory_dialog(
                parent, category_var.get(), on_subcategory_added=refresh_categories_in_dialog
            ),
            bg=THEME["accent"],
            fg="#ffffff",
            font=self._fonts["ui"],
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(pady=(0, 8))

        self._categories_refresh = refresh_categories_in_dialog

    def _set_status(self, text: str, error: bool = False):
        self.status_label.config(text=text, fg=THEME["error"] if error else THEME["text"])

    def _parse_entry_date(self, date_str: str):
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            return datetime.min

    def _on_column_sort(self, col: str):
        if self._sort_column == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col
            self._sort_reverse = False
        self._refresh_table()

    def _sort_entries(self, entries):
        col = self._sort_column

        def key_fn(e):
            if col == "date":
                return self._parse_entry_date(e["date"])
            if col == "name":
                return e["name"].lower()
            if col == "amount":
                return float(e["price"])
            if col == "type":
                return e["type"]
            if col == "cats":
                return ", ".join(s["name"] for s in e["subcategories"]).lower()
            return 0

        return sorted(entries, key=key_fn, reverse=self._sort_reverse)

    def _fetch_entries_for_filter(self):
        mode = self._filter_mode.get()
        today = datetime.now()
        if mode == "month":
            start = today.replace(day=1).strftime("%Y-%m-%d")
            last_day = monthrange(today.year, today.month)[1]
            end = today.replace(day=last_day).strftime("%Y-%m-%d")
            return self.entry_service.get_entries_by_period(start, end)
        raw = self.entry_service.get_recent_entries(400)
        if mode == "income":
            return [e for e in raw if e["type"] == "income"]
        if mode == "expense":
            return [e for e in raw if e["type"] == "expense"]
        return raw

    def _apply_search(self, entries):
        q = (self._search_var.get() or "").strip().lower()
        if not q:
            return entries
        return [e for e in entries if q in (e.get("name") or "").lower()]

    def _refresh_table(self):
        if not hasattr(self, "tree"):
            return
        entries = list(self._raw_entries)
        entries = self._apply_search(entries)
        entries = self._sort_entries(entries)
        self._entries_by_id = {e["id"]: e for e in entries}

        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, entry in enumerate(entries):
            categories_str = ", ".join(s["name"] for s in entry["subcategories"])
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert(
                "",
                "end",
                values=(
                    entry["date"],
                    entry["name"],
                    f"{entry['price']:.2f} ₽",
                    "Доход" if entry["type"] == "income" else "Расход",
                    categories_str,
                ),
                tags=(str(entry["id"]), tag),
            )

        # заголовок сортировки
        arrows = {"date": "Дата", "name": "Название", "amount": "Сумма", "type": "Тип", "cats": "Категории"}
        for c, title in arrows.items():
            suffix = ""
            if c == self._sort_column:
                suffix = " ▼" if self._sort_reverse else " ▲"
            self.tree.heading(c, text=title + suffix)

        if hasattr(self, "status_label") and getattr(self, "_last_load_ok", True):
            shown = len(entries)
            total = len(self._raw_entries)
            q = (self._search_var.get() or "").strip()
            now_str = datetime.now().strftime("%H:%M:%S")
            extra = f" · поиск «{q}»" if q else ""
            filt = self._filter_mode.get()
            self._set_status(
                f"Показано: {shown}/{total} · фильтр: {filt}{extra} · {now_str}",
                error=False,
            )

    def _load_data(self):
        try:
            today = datetime.now()
            stats = self.stats_service.get_monthly_summary(today.year, today.month)
            self.balance_label.config(text=f"{stats['balance']:.2f} ₽")
            self.income_label.config(text=f"{stats['total_income']:.2f} ₽")
            self.expense_label.config(text=f"{stats['total_expense']:.2f} ₽")

            self._raw_entries = self._fetch_entries_for_filter()
            self._last_load_ok = True
            self._last_error_msg = ""
            self._refresh_table()
            if hasattr(self, "stats_text_current"):
                self._refresh_statistics_current_tab()
            if hasattr(self, "_categories_refresh"):
                self._categories_refresh()
        except Exception as e:
            self._last_load_ok = False
            self._last_error_msg = str(e)
            self._set_status(f"Ошибка загрузки: {e}", error=True)
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные: {e}")

    def add_entry(self, entry_type, entry_id=None):
        dialog = tk.Toplevel(self.root)
        
        if entry_id:
            # Режим редактирования
            entry = self._entries_by_id.get(entry_id)
            if not entry:
                messagebox.showerror("Ошибка", "Запись не найдена")
                return
            dialog.title(f"Редактирование записи")
            title_text = "Редактировать запись"
            title_color = THEME["accent"]
            is_edit = True
        else:
            # Режим добавления
            dialog.title(f"Добавление {'дохода' if entry_type == 'income' else 'расхода'}")
            title_text = "Добавить доход" if entry_type == "income" else "Добавить расход"
            title_color = THEME["income"] if entry_type == "income" else THEME["expense"]
            is_edit = False
        
        dialog.geometry("560x460")
        dialog.minsize(520, 300)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=THEME["panel"])
        dialog.resizable(True, True)

        tk.Label(
            dialog,
            text=title_text,
            bg=THEME["panel"],
            fg=title_color,
            font=self._fonts["heading"],
        ).pack(anchor="w", padx=16, pady=(14, 8))

        form = tk.Frame(dialog, bg=THEME["panel"])
        form.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        form.columnconfigure(0, weight=0)
        form.columnconfigure(1, weight=1)

        def add_row(row, label, widget):
            tk.Label(
                form,
                text=label,
                bg=THEME["panel"],
                fg=THEME["text"],
                font=self._fonts["ui"],
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=8)
            widget.grid(row=row, column=1, sticky="ew", pady=8)

        name_entry = tk.Entry(
            form,
            font=self._fonts["ui"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
            relief=tk.FLAT,
        )

        price_entry = tk.Entry(
            form,
            font=self._fonts["ui"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
            relief=tk.FLAT,
        )

        date_entry = DateEntry(
            form,
            font=self._fonts["ui"],
            date_pattern="yyyy-mm-dd",
            background=THEME["accent"],
            foreground="white",
            borderwidth=1,
        )

        categories = self.category_service.get_all_categories()
        cat_names = [c["name"] for c in categories]

        category_var = tk.StringVar()
        subcategory_var = tk.StringVar()

        category_combo = ttk.Combobox(
            form,
            textvariable=category_var,
            values=cat_names,
            state="readonly",
            width=30,
        )

        subcategory_combo = ttk.Combobox(
            form,
            textvariable=subcategory_var,
            values=[],
            state="readonly",
            width=30,
        )

        # Если режим редактирования, заполняем поля текущими значениями
        if is_edit and entry:
            name_entry.insert(0, entry["name"])
            price_entry.insert(0, str(entry["price"]))
            try:
                # Парсим дату из формата дд.мм.гггг в объект datetime
                entry_date = datetime.strptime(entry["date"], "%d.%m.%Y").date()
                date_entry.set_date(entry_date)
            except:
                date_entry.set_date(datetime.now().date())

        add_row(0, "Название", name_entry)
        add_row(1, "Сумма", price_entry)
        add_row(2, "Дата", date_entry)
        add_row(3, "Категория", category_combo)
        add_row(4, "Подкатегория", subcategory_combo)

        hint_frame = tk.Frame(dialog, bg=THEME["panel"])
        hint_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        name_hint = tk.Label(hint_frame, text="", bg=THEME["panel"], fg=THEME["error"], font=self._fonts["small"])
        price_hint = tk.Label(hint_frame, text="", bg=THEME["panel"], fg=THEME["error"], font=self._fonts["small"])
        date_hint = tk.Label(hint_frame, text="", bg=THEME["panel"], fg=THEME["error"], font=self._fonts["small"])
        cat_hint = tk.Label(hint_frame, text="", bg=THEME["panel"], fg=THEME["error"], font=self._fonts["small"])
        subcat_hint = tk.Label(hint_frame, text="", bg=THEME["panel"], fg=THEME["error"], font=self._fonts["small"])

        name_hint.pack(anchor="w")
        price_hint.pack(anchor="w")
        date_hint.pack(anchor="w")
        cat_hint.pack(anchor="w")
        subcat_hint.pack(anchor="w")

        def clear_hints():
            for lbl in (name_hint, price_hint, date_hint, cat_hint, subcat_hint):
                lbl.config(text="")

        def set_subcategories(*args):
            selected_cat_name = category_var.get().strip()
            subcategory_var.set("")

            cat = next((c for c in categories if c["name"] == selected_cat_name), None)
            if not cat:
                subcategory_combo["values"] = []
                subcategory_combo.config(state="disabled")
                return

            subcats = cat.get("subcategories", [])
            subcategory_names = [s["name"] for s in subcats]
            subcategory_combo["values"] = subcategory_names
            subcategory_combo.config(state="readonly" if subcategory_names else "disabled")
            if not subcategory_names:
                subcategory_var.set("")

        category_var.trace_add("write", set_subcategories)

        # Инициализация категорий и подкатегорий
        if is_edit and entry and entry["subcategories"]:
            # Режим редактирования - устанавливаем текущую категорию и подкатегорию
            for subcat in entry["subcategories"]:
                cat_name = subcat.get("category_name")
                if cat_name:
                    category_var.set(cat_name)
                    set_subcategories()
                    subcategory_var.set(subcat["name"])
                    break
        elif cat_names:
            # Режим добавления - устанавливаем первую категорию
            category_var.set(cat_names[0])
            set_subcategories()
        else:
            subcategory_combo.config(state="disabled")

        btn_row = tk.Frame(dialog, bg=THEME["panel"])
        btn_row.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=14)

        def cancel():
            dialog.destroy()

        def save():
            clear_hints()
            ok = True

            name = name_entry.get().strip()
            if not name:
                name_hint.config(text="Введите название операции")
                ok = False

            try:
                price = float(price_entry.get().replace(",", "."))
                if price <= 0:
                    raise ValueError
            except ValueError:
                price_hint.config(text="Укажите положительное число")
                ok = False

            try:
                date_str = date_entry.get_date().strftime("%Y-%m-%d")
            except Exception:
                date_hint.config(text="Не удалось определить дату")
                ok = False

            selected_cat_name = category_var.get().strip()
            if not selected_cat_name:
                cat_hint.config(text="Выберите категорию")
                ok = False

            selected_subcat_name = subcategory_var.get().strip()
            if selected_cat_name:
                cat = next((c for c in categories if c["name"] == selected_cat_name), None)
                subcats = cat.get("subcategories", []) if cat else []
                if subcats and not selected_subcat_name:
                    subcat_hint.config(text="Выберите подкатегорию")
                    ok = False

            if not ok:
                return

            try:
                subcat_ids = []
                if selected_cat_name and selected_subcat_name:
                    cat = next((c for c in categories if c["name"] == selected_cat_name), None)
                    if cat:
                        subcat = next(
                            (s for s in cat.get("subcategories", []) if s["name"] == selected_subcat_name),
                            None
                        )
                        if subcat:
                            subcat_ids = [subcat["id"]]

                if is_edit and entry_id:
                    # Режим редактирования
                    self.entry_service.update_entry(
                        entry_id=entry_id,
                        name=name,
                        price=price,
                        type=entry_type,
                        subcategory_ids=subcat_ids,
                        date=date_str,
                    )
                    dialog.destroy()
                    self._load_data()
                    messagebox.showinfo("Успех", "Запись обновлена")
                else:
                    # Режим добавления
                    self.entry_service.add_entry(
                        name=name,
                        price=price,
                        type=entry_type,
                        subcategory_ids=subcat_ids,
                        date=date_str,
                    )
                    dialog.destroy()
                    self._load_data()
                    messagebox.showinfo("Успех", "Запись добавлена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

        tk.Button(
            btn_row,
            text="Отмена",
            command=cancel,
            bg=THEME["border"],
            fg=THEME["text"],
            font=self._fonts["ui"],
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(
            btn_row,
            text="Сохранить",
            command=save,
            bg=THEME["accent"],
            fg="#ffffff",
            font=self._fonts["ui"],
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.RIGHT)

        dialog.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: cancel())
        name_entry.focus_set()

    def edit_entry(self):
        """Редактировать выбранную запись"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись для редактирования")
            return
        
        item = selected[0]
        entry_id = int(self.tree.item(item, "tags")[0])
        entry = self._entries_by_id.get(entry_id)
        
        if not entry:
            messagebox.showerror("Ошибка", "Запись не найдена")
            return
        
        # Вызываем add_entry в режиме редактирования
        self.add_entry(entry_type=entry["type"], entry_id=entry_id)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        if messagebox.askyesno("Подтверждение", "Удалить выбранную запись?"):
            item = selected[0]
            entry_id = int(self.tree.item(item, "tags")[0])
            if self.entry_service.delete_entry(entry_id):
                self._load_data()
                messagebox.showinfo("Успех", "Запись удалена")

    def edit_categories(self):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        entry_id = int(self.tree.item(item, "tags")[0])
        entries = self.entry_service.get_recent_entries(200)
        entry = next((e for e in entries if e["id"] == entry_id), None)
        if entry:
            self.show_edit_categories_dialog(entry)

    def show_edit_categories_dialog(self, entry):
        dialog = tk.Toplevel(self.root)
        dialog.title("Редактирование категорий")
        dialog.geometry("440x420")
        dialog.minsize(400, 320)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=THEME["panel"])

        tk.Label(
            dialog,
            text=f"Запись: {entry['name']}",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=self._fonts["heading"],
        ).pack(pady=(12, 8), padx=14, anchor="w")

        categories_frame = tk.Frame(dialog, bg=THEME["panel"])
        categories_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)

        canvas = tk.Canvas(categories_frame, bg=THEME["panel"], highlightthickness=0)
        scrollbar = tk.Scrollbar(categories_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=THEME["panel"])
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        categories = self.category_service.get_all_categories()
        vars_dict = {}
        current_subcat_ids = [s["id"] for s in entry["subcategories"]]

        for category in categories:
            tk.Label(
                scrollable_frame,
                text=category["name"],
                bg=THEME["panel"],
                fg=THEME["text"],
                font=self._fonts["heading_small"],
            ).pack(anchor="w", pady=(6, 0))
            for subcat in category["subcategories"]:
                var = tk.BooleanVar(value=subcat["id"] in current_subcat_ids)
                cb = tk.Checkbutton(
                    scrollable_frame,
                    text=subcat["name"],
                    variable=var,
                    anchor="w",
                    bg=THEME["panel"],
                    fg=THEME["text"],
                    font=self._fonts["ui"],
                    selectcolor=THEME["panel"],
                    activebackground=THEME["panel"],
                )
                cb.pack(anchor="w", padx=(18, 0))
                vars_dict[subcat["id"]] = var

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_row = tk.Frame(dialog, bg=THEME["panel"])
        btn_row.pack(fill=tk.X, padx=14, pady=12)

        def save():
            for subcat_id in current_subcat_ids:
                self.entry_service.remove_subcategory_from_entry(entry["id"], subcat_id)
            for subcat_id, var in vars_dict.items():
                if var.get():
                    self.entry_service.add_subcategory_to_entry(entry["id"], subcat_id)
            dialog.destroy()
            self._load_data()
            messagebox.showinfo("Успех", "Категории обновлены")

        def cancel():
            dialog.destroy()

        tk.Button(
            btn_row,
            text="Отмена",
            command=cancel,
            bg=THEME["border"],
            fg=THEME["text"],
            font=self._fonts["ui"],
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(
            btn_row,
            text="Сохранить",
            command=save,
            bg=THEME["accent"],
            fg="#ffffff",
            font=self._fonts["ui"],
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.RIGHT)

        dialog.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: cancel())

    def manage_categories(self):
        self.main_notebook.select(2)

    def show_statistics(self):
        self.main_notebook.select(1)

    def add_category_dialog(self, parent, on_category_added=None):
        dialog = tk.Toplevel(parent)
        dialog.title("Добавить категорию")
        dialog.geometry("360x240")
        dialog.minsize(320, 200)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=THEME["panel"])

        tk.Label(dialog, text="Название", bg=THEME["panel"], fg=THEME["text"], font=self._fonts["ui"]).pack(anchor="w", padx=14, pady=(12, 4))
        name_entry = tk.Entry(dialog, font=self._fonts["ui"], width=36)
        name_entry.pack(padx=14)

        tk.Label(dialog, text="Тип", bg=THEME["panel"], fg=THEME["text"], font=self._fonts["ui"]).pack(anchor="w", padx=14, pady=(10, 4))
        type_var = tk.StringVar(value="expense")
        ttk.Radiobutton(dialog, text="Расход", variable=type_var, value="expense").pack(anchor="w", padx=28)
        ttk.Radiobutton(dialog, text="Доход", variable=type_var, value="income").pack(anchor="w", padx=28)

        btn_row = tk.Frame(dialog, bg=THEME["panel"])
        btn_row.pack(fill=tk.X, padx=14, pady=16)

        def save():
            name = name_entry.get().strip()
            if name:
                self.category_service.create_category(name, type_var.get())
                dialog.destroy()
                self._load_data()
                if on_category_added:
                    on_category_added()
                messagebox.showinfo("Успех", "Категория добавлена")

        def cancel():
            dialog.destroy()

        tk.Button(btn_row, text="Отмена", command=cancel, bg=THEME["border"], fg=THEME["text"], font=self._fonts["ui"], relief=tk.FLAT, padx=14, pady=6).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        tk.Button(btn_row, text="Сохранить", command=save, bg=THEME["accent"], fg="#ffffff", font=self._fonts["ui"], relief=tk.FLAT, padx=14, pady=6).pack(
            side=tk.RIGHT
        )
        dialog.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: cancel())
        name_entry.focus_set()

    def add_subcategory_dialog(self, parent, category_name, on_subcategory_added=None):
        if not category_name:
            messagebox.showerror("Ошибка", "Выберите категорию")
            return

        dialog = tk.Toplevel(parent)
        dialog.title("Добавить подкатегорию")
        dialog.geometry("380x200")
        dialog.minsize(340, 180)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=THEME["panel"])

        tk.Label(dialog, text=f"Категория: {category_name}", bg=THEME["panel"], fg=THEME["muted"], font=self._fonts["ui"]).pack(pady=(12, 4))
        tk.Label(dialog, text="Название подкатегории", bg=THEME["panel"], fg=THEME["text"], font=self._fonts["ui"]).pack(anchor="w", padx=14)
        name_entry = tk.Entry(dialog, font=self._fonts["ui"], width=36)
        name_entry.pack(padx=14, pady=6)

        btn_row = tk.Frame(dialog, bg=THEME["panel"])
        btn_row.pack(fill=tk.X, padx=14, pady=12)

        def save():
            name = name_entry.get().strip()
            if name:
                categories = self.category_service.get_all_categories()
                category = next((c for c in categories if c["name"] == category_name), None)
                if category:
                    self.category_service.create_subcategory(name, category["id"])
                    dialog.destroy()
                    self._load_data()
                    if on_subcategory_added:
                        on_subcategory_added()
                    messagebox.showinfo("Успех", "Подкатегория добавлена")

        def cancel():
            dialog.destroy()

        tk.Button(btn_row, text="Отмена", command=cancel, bg=THEME["border"], fg=THEME["text"], font=self._fonts["ui"], relief=tk.FLAT, padx=14, pady=6).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        tk.Button(btn_row, text="Сохранить", command=save, bg=THEME["accent"], fg="#ffffff", font=self._fonts["ui"], relief=tk.FLAT, padx=14, pady=6).pack(
            side=tk.RIGHT
        )
        dialog.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: cancel())
        name_entry.focus_set()

    def edit_category_dialog(self, parent, category, on_category_added=None):
        dialog = tk.Toplevel(parent)
        dialog.title("Редактировать категорию")
        dialog.geometry("360x240")
        dialog.minsize(320, 200)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=THEME["panel"])

        tk.Label(dialog, text="Название", bg=THEME["panel"], fg=THEME["text"], font=self._fonts["ui"]).pack(anchor="w", padx=14, pady=(12, 4))
        name_entry = tk.Entry(dialog, font=self._fonts["ui"], width=36)
        name_entry.insert(0, category['name'])
        name_entry.pack(padx=14)

        tk.Label(dialog, text="Тип", bg=THEME["panel"], fg=THEME["text"], font=self._fonts["ui"]).pack(anchor="w", padx=14, pady=(10, 4))
        type_var = tk.StringVar(value=category['type'])
        ttk.Radiobutton(dialog, text="Расход", variable=type_var, value="expense").pack(anchor="w", padx=28)
        ttk.Radiobutton(dialog, text="Доход", variable=type_var, value="income").pack(anchor="w", padx=28)

        btn_row = tk.Frame(dialog, bg=THEME["panel"])
        btn_row.pack(fill=tk.X, padx=14, pady=16)

        def save():
            name = name_entry.get().strip()
            if name:
                self.category_service.update_category(category["id"], name=name, type=type_var.get())
                dialog.destroy()
                self._load_data()
                if on_category_added:
                    on_category_added()
                messagebox.showinfo("Успех", "Категория обновлена")

        def cancel():
            dialog.destroy()

        tk.Button(btn_row, text="Отмена", command=cancel, bg=THEME["border"], fg=THEME["text"], font=self._fonts["ui"], relief=tk.FLAT, padx=14, pady=6).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        tk.Button(btn_row, text="Сохранить", command=save, bg=THEME["accent"], fg="#ffffff", font=self._fonts["ui"], relief=tk.FLAT, padx=14, pady=6).pack(
            side=tk.RIGHT
        )
        dialog.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: cancel())
        name_entry.focus_set()
        name_entry.select_range(0, tk.END)

    def edit_subcategory_dialog(self, parent, subcategory, category_name, on_subcategory_added=None):
        dialog = tk.Toplevel(parent)
        dialog.title("Редактировать подкатегорию")
        dialog.geometry("380x200")
        dialog.minsize(340, 180)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=THEME["panel"])

        tk.Label(dialog, text=f"Категория: {category_name}", bg=THEME["panel"], fg=THEME["muted"], font=self._fonts["ui"]).pack(pady=(12, 4))
        tk.Label(dialog, text="Название подкатегории", bg=THEME["panel"], fg=THEME["text"], font=self._fonts["ui"]).pack(anchor="w", padx=14)
        name_entry = tk.Entry(dialog, font=self._fonts["ui"], width=36)
        name_entry.insert(0, subcategory['name'])
        name_entry.pack(padx=14, pady=6)

        btn_row = tk.Frame(dialog, bg=THEME["panel"])
        btn_row.pack(fill=tk.X, padx=14, pady=12)

        def save():
            name = name_entry.get().strip()
            if name:
                self.category_service.update_subcategory(subcategory["id"], name=name)
                dialog.destroy()
                self._load_data()
                if on_subcategory_added:
                    on_subcategory_added()
                messagebox.showinfo("Успех", "Подкатегория обновлена")

        def cancel():
            dialog.destroy()

        tk.Button(btn_row, text="Отмена", command=cancel, bg=THEME["border"], fg=THEME["text"], font=self._fonts["ui"], relief=tk.FLAT, padx=14, pady=6).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        tk.Button(btn_row, text="Сохранить", command=save, bg=THEME["accent"], fg="#ffffff", font=self._fonts["ui"], relief=tk.FLAT, padx=14, pady=6).pack(
            side=tk.RIGHT
        )
        dialog.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: cancel())
        name_entry.focus_set()
        name_entry.select_range(0, tk.END)

    def delete_category_with_confirm(self, category_id, on_deleted=None):
        """Удалить категорию с подтверждением"""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить категорию?\n\nВсе её подкатегории также будут удалены."):
            if self.category_service.delete_category(category_id):
                self._load_data()
                if on_deleted:
                    on_deleted()
                messagebox.showinfo("Успех", "Категория удалена")
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить категорию")

    def delete_subcategory_with_confirm(self, subcategory_id, on_deleted=None):
        """Удалить подкатегорию с подтверждением"""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить подкатегорию?"):
            if self.category_service.delete_subcategory(subcategory_id):
                self._load_data()
                if on_deleted:
                    on_deleted()
                messagebox.showinfo("Успех", "Подкатегория удалена")
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить подкатегорию")

    def export_data(self):
        messagebox.showinfo("Информация", "Функция экспорта будет добавлена позже")

    def show_about(self):
        messagebox.showinfo(
            "О программе",
            "Budget App\nВерсия 1.0\n\nПриложение для учёта финансов\nс поддержкой категорий и подкатегорий",
        )

    def run(self):
        self.root.mainloop()
