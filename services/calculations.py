from sqlalchemy import func
from decimal import Decimal
from database.models import Order, Expense, TreasuryMovement, BusinessDay, PaymentMethod, ExpenseSource, MovementType, TreasuryType

def get_decimal_sum(result):
    return Decimal(result or 0.00)

# ==========================================
# 1. حسابات الإيرادات (تجمع كل المدفوع حتى لو اشتراك)
# ==========================================

def calculate_cash_revenue(session, business_day_id: int) -> Decimal:
    """إيراد الكاش: مجموع كل الطلبات المدفوعة كاش بما فيها تمن الاشتراكات"""
    result = session.query(func.sum(Order.price)).filter(
        Order.business_day_id == business_day_id,
        Order.payment_method == PaymentMethod.cash
    ).scalar()
    return get_decimal_sum(result)

def calculate_insta_revenue(session, business_day_id: int) -> Decimal:
    """إيراد انستا: مجموع كل الطلبات المدفوعة انستا بما فيها تمن الاشتراكات"""
    result = session.query(func.sum(Order.price)).filter(
        Order.business_day_id == business_day_id,
        Order.payment_method == PaymentMethod.insta
    ).scalar()
    return get_decimal_sum(result)

def calculate_total_revenue(session, business_day_id: int) -> Decimal:
    return calculate_cash_revenue(session, business_day_id) + calculate_insta_revenue(session, business_day_id)

# ==========================================
# 2. حسابات المصروفات
# ==========================================

def calculate_expenses_by_source(session, business_day_id: int, source: ExpenseSource) -> Decimal:
    result = session.query(func.sum(Expense.amount)).filter(
        Expense.business_day_id == business_day_id,
        Expense.source == source
    ).scalar()
    return get_decimal_sum(result)

# ==========================================
# 3. حسابات حركات العهدة (إضافة / سحب)
# ==========================================

def calculate_treasury_net_movements(session, business_day_id: int, treasury_type: TreasuryType) -> Decimal:
    additions = session.query(func.sum(TreasuryMovement.amount)).filter(
        TreasuryMovement.business_day_id == business_day_id,
        TreasuryMovement.treasury_type == treasury_type,
        TreasuryMovement.movement_type == MovementType.addition
    ).scalar()
    
    withdrawals = session.query(func.sum(TreasuryMovement.amount)).filter(
        TreasuryMovement.business_day_id == business_day_id,
        TreasuryMovement.treasury_type == treasury_type,
        TreasuryMovement.movement_type == MovementType.withdrawal
    ).scalar()
    
    return get_decimal_sum(additions) - get_decimal_sum(withdrawals)

# ==========================================
# 4. حسابات الأرصدة الحالية
# ==========================================

def calculate_inside_balance(session, business_day_id: int) -> Decimal:
    day = session.query(BusinessDay).get(business_day_id)
    if not day: return Decimal(0.00)
    
    opening = Decimal(day.opening_inside or 0.00)
    cash_revenue = calculate_cash_revenue(session, business_day_id)
    expenses_from_inside = calculate_expenses_by_source(session, business_day_id, ExpenseSource.inside)
    
    return opening + cash_revenue - expenses_from_inside

def calculate_cash_treasury_balance(session, business_day_id: int) -> Decimal:
    day = session.query(BusinessDay).get(business_day_id)
    if not day: return Decimal(0.00)
    
    opening = Decimal(day.opening_cash_treasury or 0.00)
    net_movements = calculate_treasury_net_movements(session, business_day_id, TreasuryType.cash)
    expenses_from_cash = calculate_expenses_by_source(session, business_day_id, ExpenseSource.cash_treasury)
    
    return opening + net_movements - expenses_from_cash

def calculate_insta_treasury_balance(session, business_day_id: int) -> Decimal:
    day = session.query(BusinessDay).get(business_day_id)
    if not day: return Decimal(0.00)
    
    opening = Decimal(day.opening_insta_treasury or 0.00)
    net_movements = calculate_treasury_net_movements(session, business_day_id, TreasuryType.insta)
    expenses_from_insta = calculate_expenses_by_source(session, business_day_id, ExpenseSource.insta_treasury)
    
    return opening + net_movements - expenses_from_insta

def calculate_total_responsibility(session, business_day_id: int) -> Decimal:
    return (
        calculate_inside_balance(session, business_day_id) +
        calculate_cash_treasury_balance(session, business_day_id) +
        calculate_insta_treasury_balance(session, business_day_id)
    )
