from sqlalchemy import Column, Integer, String, Boolean, Date, Float
from app.db import Base
from datetime import date

class UserProfile(Base):
    __tablename__ = "user_profile"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Iulian")
    level = Column(Integer, default=1)
    xp_current = Column(Integer, default=0)
    monthly_budget = Column(Float, default=3000.0)
    smoking_start_date = Column(Date, default=date.today)

class DailyLog(Base):
    __tablename__ = "daily_logs"
    id = Column(Integer, primary_key=True, index=True)
    log_date = Column(Date, unique=True, default=date.today, index=True)

    # Core Habits
    prog_completed = Column(Boolean, default=False)
    plc_completed = Column(Boolean, default=False)
    elec_completed = Column(Boolean, default=False)
    project_completed = Column(Boolean, default=False)
    gym_completed = Column(Boolean, default=False)
    review_completed = Column(Boolean, default=False)

    # Module Măsurabile
    cigarettes_count = Column(Integer, default=0)
    routine_morning = Column(Boolean, default=False)
    routine_evening = Column(Boolean, default=False)
    expenses_total = Column(Float, default=0.0)

# TABELĂ NOUĂ PENTRU LOG-UL MESELOR
class MealLog(Base):
    __tablename__ = "meal_logs"
    id = Column(Integer, primary_key=True, index=True)
    log_date = Column(Date, default=date.today, index=True)
    meal_time = Column(String)  # Stochează automat ora (ex: "14:20")
    meal_name = Column(String)  # Ex: "Omletă + Shake Bulk"
    calories = Column(Integer)