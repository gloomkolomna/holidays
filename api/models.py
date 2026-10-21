from __future__ import annotations
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    vk_id = Column(Integer, primary_key=True)
    role = Column(String, nullable=False, default="player", server_default="player")
    status = Column(String, nullable=False, default="active", server_default="active")
    display_name = Column(String, nullable=True)
    crystals = Column(Integer, nullable=False, default=0, server_default="0")
    music_enabled = Column(Boolean, nullable=False, default=True, server_default="1")
    is_member = Column(Boolean, nullable=True)
    member_cached_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    bg_image_url = Column(String, nullable=True)
    bg_color = Column(String, nullable=True)
    palette = Column(Text, nullable=True)
    animation_preset = Column(String, nullable=True)
    animation_url = Column(String, nullable=True)
    animation_size = Column(Integer, nullable=False, default=50, server_default="50")
    audio_url = Column(String, nullable=True)
    trophy_image_url = Column(String, nullable=True)
    shop_enabled = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow)

    categories = relationship(
        "HolidayCategory", back_populates="holiday", cascade="all, delete-orphan",
        order_by="HolidayCategory.id",
    )


class HolidayCategory(Base):
    __tablename__ = "holiday_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    holiday_id = Column(Integer, ForeignKey("holidays.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    norm_crosses = Column(Integer, nullable=False, default=1000, server_default="1000")
    created_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow)

    holiday = relationship("Holiday", back_populates="categories")
    cards = relationship(
        "HolidayCard", back_populates="category", cascade="all, delete-orphan",
        order_by="HolidayCard.day",
    )


class HolidayCard(Base):
    __tablename__ = "holiday_cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    holiday_id = Column(Integer, ForeignKey("holidays.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("holiday_categories.id", ondelete="CASCADE"), nullable=False)
    day = Column(String, nullable=True)
    is_trophy = Column(Boolean, nullable=False, default=False, server_default="0")
    title = Column(String, nullable=False, default="", server_default="")
    task_text = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow)

    holiday = relationship("Holiday")
    category = relationship("HolidayCategory", back_populates="cards")

    __table_args__ = (
        UniqueConstraint("category_id", "day", name="uq_holidaycard_category_day"),
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    holiday_id = Column(Integer, ForeignKey("holidays.id", ondelete="CASCADE"), nullable=False)
    card_id = Column(Integer, ForeignKey("holiday_cards.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String, nullable=False, default="daily", server_default="daily")
    required_crosses = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="active", server_default="active")
    taken_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow)
    done_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("uq_tasks_one_active", "user_id", unique=True, sqlite_where=text("status = 'active'")),
    )


class UserCard(Base):
    __tablename__ = "user_cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    card_id = Column(Integer, ForeignKey("holiday_cards.id", ondelete="CASCADE"), nullable=False)
    source = Column(String, nullable=False, default="daily", server_default="daily")
    earned_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "card_id", name="uq_usercard_user_card"),
    )


class StitchReport(Base):
    __tablename__ = "stitch_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, nullable=True)
    amount = Column(Integer, nullable=False)
    photo_before = Column(String, nullable=True)
    photo_after = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow, index=True)


class CollectionReward(Base):
    __tablename__ = "collection_rewards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    holiday_id = Column(Integer, ForeignKey("holidays.id", ondelete="CASCADE"), nullable=False)
    crystals = Column(Integer, nullable=False, default=1, server_default="1")
    awarded_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "holiday_id", name="uq_collectionreward_user_holiday"),
    )


class RewardItem(Base):
    __tablename__ = "reward_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    price_crystals = Column(Integer, nullable=False, default=1, server_default="1")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow)


class RewardCode(Base):
    __tablename__ = "reward_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("reward_items.id", ondelete="CASCADE"), nullable=False)
    code = Column(String, nullable=False)
    taken_by = Column(Integer, nullable=True)
    taken_at = Column(DateTime, nullable=True)


class RewardPurchase(Base):
    __tablename__ = "reward_purchases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("reward_items.id", ondelete="CASCADE"), nullable=False)
    code_id = Column(Integer, ForeignKey("reward_codes.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow)


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)
    level = Column(String, nullable=False, default="info", server_default="info")
    event = Column(String, nullable=True)
    method = Column(String, nullable=True)
    path = Column(String, nullable=True)
    status_code = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    user_id = Column(Integer, nullable=True)
    client_ip = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=__import__("datetime").datetime.utcnow, index=True)
