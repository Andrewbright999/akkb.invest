from __future__ import annotations
from datetime import date, datetime
from typing import Optional

from decimal import Decimal
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Date, DateTime, Integer, Float, UniqueConstraint, Index, BigInteger, ForeignKey, Numeric, CheckConstraint


from sqlalchemy.orm import relationship



class Base(DeclarativeBase):
    pass


# Ценные бумаги / инструменты
class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    secid: Mapped[str] = mapped_column(String(32), index=True)
    board: Mapped[str] = mapped_column(String(16), default="TQBR", index=True)

    name: Mapped[str] = mapped_column(String(255))
    shortname: Mapped[str] = mapped_column(String(128), default="")
    isin: Mapped[str] = mapped_column(String(32), default="")
    lotsize: Mapped[int] = mapped_column(Integer, default=1)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint("secid", "board", name="uq_instrument"),
    )

# Свечи
class Candle(Base):
    __tablename__ = "candles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    secid: Mapped[str] = mapped_column(String(32), index=True)
    board: Mapped[str] = mapped_column(String(16), default="TQBR", index=True)
    interval: Mapped[int] = mapped_column(Integer, index=True)
    d: Mapped[date] = mapped_column(Date, index=True)

    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    source: Mapped[str] = mapped_column(String(16), default="moex")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("secid", "board", "interval", "d", name="uq_candle"),
        Index("ix_candle_lookup", "secid", "board", "interval", "d"),
    )

#Свечи в кэш. 
class CandleCache(Base):
    __tablename__ = "candle_cache"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    secid: Mapped[str] = mapped_column(String(32), index=True)
    board: Mapped[str] = mapped_column(String(16), default="TQBR", index=True)
    interval: Mapped[int] = mapped_column(Integer, index=True)

    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint("secid", "board", "interval", "date_from", "date_to", name="uq_cache_range"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    # стартовый баланс 10000
    cash: Mapped[float] = mapped_column(Float, default=10000.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True)

    qty: Mapped[float] = mapped_column(Float, default=0.0)
    avg_price: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint("account_id", "instrument_id", name="uq_position"),
    )


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True)

    side: Mapped[str] = mapped_column(String(4))  # BUY/SELL
    qty: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        CheckConstraint("side IN ('BUY','SELL')", name="ck_trade_side"),
        Index("ix_trade_acc_time", "account_id", "created_at"),
    )
