from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Table, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from src.core.database import Base

# Таблица для связи многие-ко-многим между entries и subcategories
# Только ОДНО определение таблицы!
entry_subcategory_table = Table('entries_subcategories', Base.metadata,
                                Column('entry_id', Integer, ForeignKey('entries.id', ondelete='CASCADE'),
                                       primary_key=True),
                                Column('subcategory_id', Integer, ForeignKey('subcategories.id', ondelete='CASCADE'),
                                       primary_key=True),
                                extend_existing=True  # Добавляем этот параметр на всякий случай
                                )


class Category(Base):
    """Модель категории (Продукты, Транспорт, и т.д.)"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # 'income' или 'expense'
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    subcategories = relationship("Subcategory", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("type IN ('income', 'expense')", name='check_category_type'),
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', type='{self.type}')>"


class Subcategory(Base):
    """Модель подкатегории (Молочные продукты, Такси, и т.д.)"""
    __tablename__ = 'subcategories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    category = relationship("Category", back_populates="subcategories")
    entries = relationship("Entry", secondary=entry_subcategory_table, back_populates="subcategories")

    def __repr__(self):
        return f"<Subcategory(id={self.id}, name='{self.name}')>"


class Entry(Base):
    """Модель записи/товара"""
    __tablename__ = 'entries'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    type = Column(String(50), nullable=False)  # 'income' или 'expense'
    date = Column(Date, nullable=False, default=datetime.now().date())
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связи
    subcategories = relationship("Subcategory", secondary=entry_subcategory_table, back_populates="entries")

    __table_args__ = (
        CheckConstraint("price >= 0", name='check_price_positive'),
        CheckConstraint("type IN ('income', 'expense')", name='check_entry_type'),
    )

    def __repr__(self):
        return f"<Entry(id={self.id}, name='{self.name}', price={self.price}, type='{self.type}')>"

# УДАЛЯЕМ ЭТОТ КЛАСС - он не нужен!
# class EntrySubcategory(Base):
#     """Модель для связи Entry и Subcategory"""
#     __tablename__ = 'entries_subcategories'
#
#     entry_id = Column(Integer, ForeignKey('entries.id', ondelete='CASCADE'), primary_key=True)
#     subcategory_id = Column(Integer, ForeignKey('subcategories.id', ondelete='CASCADE'), primary_key=True)