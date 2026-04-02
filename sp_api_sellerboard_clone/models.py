from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    purchase_date: Mapped[date] = mapped_column(Date, index=True)
    sku: Mapped[str] = mapped_column(String(128), index=True)
    asin: Mapped[str] = mapped_column(String(32), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    item_price: Mapped[float] = mapped_column(Float)
    amazon_fee: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Cogs(Base):
    __tablename__ = "cogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    unit_cogs: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdSpend(Base):
    __tablename__ = "ad_spend"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spend_date: Mapped[date] = mapped_column(Date, index=True)
    sku: Mapped[str] = mapped_column(String(128), index=True)
    amount: Mapped[float] = mapped_column(Float)


def build_session_factory(database_url: str):
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
