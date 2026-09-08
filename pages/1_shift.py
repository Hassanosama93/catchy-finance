import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database.connection import get_db
from database.models import Order, Expense, PaymentMethod, ExpenseSource, BusinessDay, Employee, ExpenseCategory
from services.calculations import (
    calculate_cash_revenue, calculate_insta_revenue, calculate_total_revenue,
    calculate_expenses_by_source, calculate_inside_balance,
    calculate_cash_treasury_balance, calculate_insta_treasury_balance,
    calculate_total_responsibility
)

# كود CSS مخصص للموبايل لجعل الأزرار والقوائم كبيرة ومريحة للمس
st.markdown("""
<style>
    @media (max-width: 768px) {
        /* تكبير الأزرار للموبايل */
        .stButton>button {
            min-height: 48px !important;
            font-size: 16px !important;
            width: 100% !important;
        }
        /* تكبير حقول الإدخال والأسهم لسهولة الضغط */
        input, select, div[data-baseweb="select"] {
            min-height: 45px !important;
            font-size: 16px !important;
        }
        /* ترتيب الكروت 2 في السطر على الموبايل */
        div[data-testid="column"] {
            flex: 1 1 calc(50% - 10px) !important;
            min-width: 130px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

if 'current_region_id' not in st.session_state:
    st.warning("الرجاء اختيار المنطقة من الصفحة الرئيسية أولاً.")
    st.stop()

region_id = st.session_state['current_region_id']
db = next(get_db())

st.title(f"Shift - {st.session_state['current_region_name']}")

selected_date = st.date_input("📅 تاريخ اليوم:", date.today())

current_day = db.query(BusinessDay).filter(
    BusinessDay.region_id == region_id, BusinessDay.business_date == selected_date
).first()

if not current_day:
    yesterday = selected_date - timedelta(days=1)
    prev_day = db.query(BusinessDay).filter(BusinessDay.region_id == region_id, BusinessDay.business_date == yesterday).first()
    
    current_day = BusinessDay(
        region_id=region_id, business_date=selected_date, status="OPEN",
        opening_inside=prev_day.closing_inside if prev_day else 0.0,
        opening_cash_treasury=prev_day.closing_cash_treasury if prev_day else 0.0,
        opening_insta_treasury=prev_day.closing_insta_treasury if prev_day else 0.0
    )
    db.add(current_day)
    db.commit()

is_closed = (current_day.status == "CLOSED")

# ==========================================
# 1. رصيد بداية اليوم
# ==========================================
st.subheader("🌅 رصيد بداية اليوم")
col_b1, col_b2, col_b3 = st.columns(3)
col_b1.metric("الداخل", f"{current_day.opening_inside:,.2f} ج.م")
col_b2.metric("عهدة كاش", f"{current_day.opening_cash_treasury:,.2f} ج.م")
col_b3.metric("عهدة انستا", f"{current_day.opening_insta_treasury:,.2f} ج.م")
st.markdown("---")

# ==========================================
# 2. قسم الطلبات (إدخال سريع للموبايل بلمسة واحدة)
# ==========================================
st.subheader("📋 الطلبات")

# عدادات الإيراد
cash_rev = calculate_cash_revenue(db, current_day.id)
insta_rev = calculate_insta_revenue(db, current_day.id)
total_rev = calculate_total_revenue(db, current_day.id)

rev1, rev2, rev3 = st.columns(3)
rev1.metric("كاش", f"{cash_rev:,.2f} ج.م")
rev2.metric("انستا", f"{insta_rev:,.2f} ج.م")
rev3.metric("الإجمالي", f"{total_rev:,.2f} ج.م")

time_slots = [
    "3:00 - 4:00", "3:00 - 4:30", "4:00 - 5:00", "5:00 - 6:00", "5:00 - 6:30",
    "6:00 - 7:00", "6:30 - 8:00", "7:00 - 8:00", "8:00 - 9:00", "8:00 - 9:30",
    "9:00 - 10:00", "9:30 - 11:00", "10:00 - 11:00", "10:00 - 11:30", "11:00 - 12:00",
    "11:30 - 1:00", "12:00 - 1:30", "1:00 - 2:00", "1:30 - 3:00", "2:00 - 3:00"
]

# نموذج الإدخال السريع (لمسة واحدة للقوائم)
if not is_closed:
    with st.expander("➕ إضافة طلب جديد (سريع)", expanded=True):
        with st.form("quick_order_form", clear_on_submit=True):
            o_col1, o_col2 = st.columns(2)
            with o_col1:
                o_time = st.selectbox("الوقت ⏰", time_slots)
                o_name = st.text_input("اسم العميل 👤")
                o_sub = st.checkbox("☑️ اشتراك ")
            with o_col2:
                o_price = st.number_input("السعر  💵", min_value=0.0, step=10.0)
                o_pay = st.selectbox("طريقة الدفع 💳", ["Cash", "Insta", "None"])
                o_notes = st.text_input("ملاحظات  📝")
                
            if st.form_submit_button("حفظ الطلب 💾", type="primary", use_container_width=True):
                pm = PaymentMethod.none
                if not o_sub:
                    if o_pay == "Cash": pm = PaymentMethod.cash
                    elif o_pay == "Insta": pm = PaymentMethod.insta
                    
                db.add(Order(
                    business_day_id=current_day.id,
                    order_time=o_time,
                    customer_name=o_name.strip() if o_name else "بدون اسم",
                    is_subscription=o_sub,
                    price=0.0 if o_sub else o_price,
                    payment_method=pm,
                    notes=o_notes
                ))
                db.commit()
                st.success("تم حفظ الطلب!")
                st.rerun()

# عرض الطلبات المسجلة اليوم مع إمكانية حذف أي طلب
orders = db.query(Order).filter(Order.business_day_id == current_day.id).all()
if orders:
    st.write(f"##### الطلبات المسجلة ({len(orders)} طلب):")
    for o in orders:
        c_ord1, c_ord2, c_ord3, c_ord4 = st.columns([2, 3, 2, 1])
        c_ord1.write(f"⏰ {o.order_time}")
        c_ord2.write(f"👤 {o.customer_name} {'(اشتراك)' if o.is_subscription else ''}")
        c_ord3.write(f"💰 {o.price} ج.م ({o.payment_method.value})")
        if not is_closed:
            if c_ord4.button("❌", key=f"del_ord_{o.id}"):
                db.delete(o)
                db.commit()
                st.rerun()
        st.divider()
else:
    st.info("لا توجد طلبات مسجلة اليوم حتى الآن.")

st.markdown("---")

# ==========================================
# 3. إدارة الخارج
# ==========================================
st.subheader("💸 الخارج")

employees = db.query(Employee).filter(Employee.is_active == True).all()
emp_names = [e.name for e in employees] if employees else ["بدون موظف"]

categories = db.query(ExpenseCategory).filter(ExpenseCategory.is_active == True).all()
cat_names = [c.name for c in categories] if categories else ["عام"]

if not is_closed:
    with st.expander("➕ إضافة خارج جديد", expanded=False):
        with st.form("expense_form", clear_on_submit=True):
            ec1, ec2 = st.columns(2)
            with ec1:
                expense_emp = st.selectbox("الموظف ", emp_names)
                expense_type = st.selectbox("نوع الخارج", cat_names)
                expense_amount = st.number_input("المبلغ", min_value=0.0, step=10.0)
            with ec2:
                expense_source = st.selectbox("يُخصم من", ["الداخل", "عهدة كاش", "عهدة انستا"])
                expense_notes = st.text_area("تفاصيل / ملاحظات")
                
            if st.form_submit_button("تسجيل الخارج ⬇️", use_container_width=True):
                if expense_amount > 0:
                    src = ExpenseSource.inside
                    if expense_source == "عهدة كاش": src = ExpenseSource.cash_treasury
                    elif expense_source == "عهدة انستا": src = ExpenseSource.insta_treasury
                    
                    db.add(Expense(
                        business_day_id=current_day.id, person_entity=expense_emp, expense_type=expense_type,
                        amount=expense_amount, source=src, description=expense_notes
                    ))
                    db.commit()
                    st.rerun()

expenses = db.query(Expense).filter(Expense.business_day_id == current_day.id).all()
if expenses:
    for e in expenses:
        col_ex1, col_ex2, col_ex3 = st.columns([3, 3, 1])
        col_ex1.write(f"👤 **{e.person_entity}** ({e.expense_type})")
        col_ex2.write(f"💸 {e.amount} ج.م من ({e.source.value})")
        if not is_closed:
            if col_ex3.button("❌", key=f"del_exp_{e.id}"):
                db.delete(e)
                db.commit()
                st.rerun()
        st.divider()

st.markdown("---")

# ==========================================
# 4. رصيد نهاية اليوم
# ==========================================
st.subheader("📊 رصيد نهاية اليوم")

curr_inside = calculate_inside_balance(db, current_day.id)
curr_cash_treasury = calculate_cash_treasury_balance(db, current_day.id)
curr_insta_treasury = calculate_insta_treasury_balance(db, current_day.id)
total_resp = calculate_total_responsibility(db, current_day.id)

rc1, rc2, rc3 = st.columns(3)
rc1.info(f"**داخل:** {curr_inside:,.2f} ج.م")
rc2.info(f"**عهدة كاش:** {curr_cash_treasury:,.2f} ج.م")
rc3.info(f"**عهدة انستا:** {curr_insta_treasury:,.2f} ج.م")

st.warning(f"### 🛡️ إجمالي الفلوس: {total_resp:,.2f} ج.م")

if not is_closed:
    if st.button("🔒 إغلاق الشيفت", type="primary", use_container_width=True):
        current_day.status = "CLOSED"
        current_day.closing_inside = curr_inside
        current_day.closing_cash_treasury = curr_cash_treasury
        current_day.closing_insta_treasury = curr_insta_treasury
        db.commit()
        st.success("تم إغلاق الشيفت بنجاح!")
        st.rerun()

db.close()
