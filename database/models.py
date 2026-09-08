import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Enum, Numeric, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# --- Enums (القوائم الثابتة) ---
class ExpenseSource(enum.Enum):
    inside = "الداخل"
    cash_treasury = "عهدة Cash"
    insta_treasury = "عهدة Insta"

class PaymentMethod(enum.Enum):
    cash = "Cash"
    insta = "Insta"
    none = "None"

class MovementType(enum.Enum):
    addition = "إضافة"
    withdrawal = "سحب"

class TreasuryType(enum.Enum):
    cash = "عهدة Cash"
    insta = "عهدة Insta"

# --- Tables (الجداول) ---

class Region(Base):
    __tablename__ = 'regions'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)

class BusinessDay(Base):
    __tablename__ = 'business_days'
    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=False)
    business_date = Column(Date, nullable=False)
    status = Column(String, default="OPEN")
    
    opening_inside = Column(Numeric(10, 2), default=0.00)
    opening_cash_treasury = Column(Numeric(10, 2), default=0.00)
    opening_insta_treasury = Column(Numeric(10, 2), default=0.00)
    
    closing_inside = Column(Numeric(10, 2), nullable=True)
    closing_cash_treasury = Column(Numeric(10, 2), nullable=True)
    closing_insta_treasury = Column(Numeric(10, 2), nullable=True)
    closed_at = Column(DateTime, nullable=True)

class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True)
    is_active = Column(Boolean, default=True)

class ExpenseCategory(Base):
    __tablename__ = 'expense_categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    business_day_id = Column(Integer, ForeignKey('business_days.id'), nullable=False)
    order_time = Column(String, nullable=False)
    customer_name = Column(String, nullable=True)
    is_subscription = Column(Boolean, default=False)
    price = Column(Numeric(10, 2), default=0.00)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    notes = Column(String, nullable=True)

class Expense(Base):
    __tablename__ = 'expenses'
    id = Column(Integer, primary_key=True)
    business_day_id = Column(Integer, ForeignKey('business_days.id'), nullable=False)
    person_entity = Column(String, nullable=False) 
    expense_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    source = Column(Enum(ExpenseSource), nullable=False)
    notes = Column(String, nullable=True)

class TreasuryMovement(Base):
    __tablename__ = 'treasury_movements'
    id = Column(Integer, primary_key=True)
    business_day_id = Column(Integer, ForeignKey('business_days.id'), nullable=False)
    treasury_type = Column(Enum(TreasuryType), nullable=False) 
    movement_type = Column(Enum(MovementType), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(String, nullable=True)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    entity = Column(String, nullable=False)
    details = Column(String, nullable=False)
