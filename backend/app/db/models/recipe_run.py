import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.models.base import Base


class RecipeRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    INFEASIBLE = "infeasible"
    ERROR = "error"

def enum_values(enum_cls):
    return [member.value for member in enum_cls]

class RecipeRun(Base):
    __tablename__ = "recipe_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    owner_uid = Column(
        String(128),
        ForeignKey("users.uid", ondelete="CASCADE"),
        nullable=False,
    )
    pet_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pets.id", ondelete="SET NULL"),
        nullable=True,
    )

    life_stage = Column(Text, nullable=False)
    daily_calories_kcal = Column(Numeric(10, 2), nullable=False)
    timezone = Column(String(64), nullable=False, default="America/Los_Angeles")

    # input_snapshot: generation request payload (pet profile + params)
    input_snapshot = Column(JSONB, nullable=False, default=dict)
    # policy_snapshot: full recipe result payload
    policy_snapshot = Column(JSONB, nullable=False, default=dict)

    is_saved = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        SAEnum(RecipeRunStatus, name="recipe_run_status", values_callable=enum_values, create_type=False),
        nullable=False,
        default=RecipeRunStatus.PENDING,
    )

    error_message = Column(Text, nullable=True)

    solver_name = Column(Text, nullable=True)
    solve_time_ms = Column(Integer, nullable=True)
    objective_value = Column(Numeric(18, 6), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    pet = relationship("Pet", back_populates="recipe_runs")
    items = relationship("RecipeItem", back_populates="run", cascade="all, delete-orphan")
    nutrients = relationship("RecipeNutrient", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_recipe_runs_owner_created", "owner_uid", "created_at"),
        Index("idx_recipe_runs_pet_created", "pet_id", "created_at"),
        Index("idx_recipe_runs_status", "status"),
    )


class RecipeItem(Base):
    """Normalized ingredient rows per recipe run (populated when ingredient FK can be resolved)."""

    __tablename__ = "recipe_items"

    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recipe_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ingredient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    grams = Column(Numeric(12, 3), nullable=False)
    grams_basis = Column(Text, nullable=False, default="as_fed")

    food_group = Column(Text, nullable=True)
    diversity_cluster = Column(Text, nullable=True)
    roles = Column(JSONB, nullable=False, default=list)
    risk_flags = Column(JSONB, nullable=False, default=list)

    is_reusable = Column(Boolean, nullable=True)
    max_days_per_week = Column(Integer, nullable=True)
    min_gap_days = Column(Integer, nullable=True)

    run = relationship("RecipeRun", back_populates="items")

    __table_args__ = (
        Index("idx_recipe_items_run", "run_id"),
        Index("idx_recipe_items_ing", "ingredient_id"),
    )


class RecipeNutrient(Base):
    """Normalized nutrient totals per recipe run."""

    __tablename__ = "recipe_nutrients"

    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recipe_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    nutrient_id = Column(
        Integer,
        ForeignKey("nutrients.nutrient_id", ondelete="RESTRICT"),
        primary_key=True,
    )

    total_amount = Column(Numeric(18, 6), nullable=False)
    unit_name = Column(String(16), nullable=True)
    per_1000_kcal = Column(Numeric(18, 6), nullable=True)
    source = Column(String(32), nullable=False, default="computed")

    run = relationship("RecipeRun", back_populates="nutrients")

    __table_args__ = (
        Index("idx_recipe_nutrients_run", "run_id"),
        Index("idx_recipe_nutrients_nutrient", "nutrient_id"),
    )
