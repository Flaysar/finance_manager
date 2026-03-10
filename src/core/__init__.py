from src.core.config import settings
from src.core.database import Base, engine, SessionLocal, get_db, init_db
from src.core.models import Category, Subcategory, Entry  # Убрали EntrySubcategory