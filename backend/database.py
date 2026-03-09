"""Database configuration - async SQLite with SQLAlchemy."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leadsite.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency that yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        from models.lead import Lead, LeadDetail
        from models.mockup import Mockup
        from models.email_draft import EmailDraft
        from models.activity import Activity
        from models.settings import Setting
        await conn.run_sync(Base.metadata.create_all)
