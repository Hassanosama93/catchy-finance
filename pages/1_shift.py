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

if 'current_region_id' not in st.session_state:
    st.warning("الرجاء اختيار المنطقة من الصفحة الرئيسية أولاً.")
    st.stop()

region_id = st.session_state['current_region_id']
db = next(get_db())

# تم التغيير لـ Shift
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
# 1. رصيد بداية اليوم (مسميات مباشرة بدون رغي)
# ==========================================
st.subheader("🌅 رصيد بداية اليوم")
col_b1, col_b2, col_b3 = st.columns(3)
col_b1.metric("الداخل", f"{current_day.opening_inside:,.2f} ج.م")
col_b2.metric("عهدة كاش", f"{current_day.opening_cash_treasury:,.2f} ج.م")
col_b3.metric("عهدة انستا", f"{current_day.opening_insta_treasury:,.2f} ج.م")
st.markdown("---")

# ==========================================
# 2. جدول الطلبات
# ==========================================
st.subheader("📋 الطلبات")

existing_orders = db.query(Order).filter(Order.business_day_id == current_day.id).all()
data = []
if existing_orders:
    for o in existing_orders:
        data.append({
            "الوقت": o.order_time, "اسم العميل": o.customer_name or "",
            "اشتراك": o.is_subscription, "السعر": float(o.price),
            "طريقة الدفع": o.payment_method.value, "ملاحظات": o.notes or ""
        })
else:
    for _ in range(12):
        data.append({"الوقت": None, "اسم العميل": "", "اشتراك": False, "السعر": 0.0, "طريقة الدفع": "None", "ملاحظات": ""})

df_orders = pd.DataFrame(data)

# مواعيد أوسع لتغطية اليوم بالكامل
time_slots = [
    "3:00 - 4:00",
    "3:00 - 4:30",
    "4:00 - 5:00",
    "5:00 - 6:00",
    "5:00 - 6:30",
    "6:00 - 7:00",
    "6:30 - 8:00",
    "7:00 - 8:00",
    "8:00 - 9:00",
    "8:00 - 9:30",
    "9:00 - 10:00",
    "9:30 - 11:00",
    "10:00 - 11:00",
    "10:00 - 11:30",
    "11:00 - 12:00",
    "11:30 - 1:00",
    "12:00 - 1:30",
    "1:00 - 2:00",
    "1:30 - 3:00",
    "2:00 - 3:00"
]

edited_orders = st.data_editor(
    df_orders,
    column_config={
        "الوقت": st.column_config.SelectboxColumn("الوقت", options=time_slots, required=False),
        "اسم العميل": st.column_config.TextColumn("اسم العميل"),
        "اشتراك": st.column_config.CheckboxColumn("اشتراك"),
        "السعر": st.column_config.NumberColumn("السعر", min_value=0.0),
        "طريقة الدفع": st.column_config.SelectboxColumn("طريقة الدفع", options=["Cash", "Insta", "None"], required=True),
        "ملاحظات": st.column_config.TextColumn("ملاحظات")
    },
    num_rows="dynamic", use_container_width=True, disabled=is_closed, key="orders_editor"
)

if not is_closed and st.button("💾 حفظ تعديلات الطلبات", type="primary"):
    db.query(Order).filter(Order.business_day_id == current_day.id).delete()
    orders_to_add = []
    for _, row in edited_orders.iterrows():
        if pd.isna(row["الوقت"]) and str(row["اسم العميل"]).strip() == "": continue
        pm = PaymentMethod.none
        if row["طريقة الدفع"] == "Cash": pm = PaymentMethod.cash
        elif row["طريقة الدفع"] == "Insta": pm = PaymentMethod.insta
        
        orders_to_add.append(Order(
            business_day_id=current_day.id, order_time=str(row["الوقت"]), customer_name=str(row["اسم العميل"]),
            is_subscription=bool(row["اشتراك"]), price=0.0 if row["اشتراك"] else float(row["السعر"]),
            payment_method=pm, notes=str(row["ملاحظات"])
        ))
    db.add_all(orders_to_add)
    db.commit()
    st.rerun()

# الإيرادات تحت الجدول مباشرة بمسميات: كاش - انستا - الإجمالي
cash_rev = calculate_cash_revenue(db, current_day.id)
insta_rev = calculate_insta_revenue(db, current_day.id)
total_rev = calculate_total_revenue(db, current_day.id)

rev1, rev2, rev3 = st.columns(3)
rev1.metric("كاش", f"{cash_rev:,.2f} ج.م")
rev2.metric("انستا", f"{insta_rev:,.2f} ج.م")
rev3.metric("الإجمالي", f"{total_rev:,.2f} ج.م")

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
    with st.expander("➕ إضافة خارج جديد", expanded=True):
        with st.form("expense_form", clear_on_submit=True):
            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                expense_emp = st.selectbox("الموظف / الشخص", emp_names)
                expense_type = st.selectbox("نوع الخارج", cat_names)
            with ec2:
                expense_amount = st.number_input("المبلغ", min_value=0.0, step=10.0)
                expense_source = st.selectbox("يُخصم من", ["الداخل", "عهدة كاش", "عهدة انستا"])
            with ec3:
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
    exp_data = [{"الموظف": e.person_entity, "النوع": e.expense_type, "المبلغ": float(e.amount), "المصدر": e.source.value, "ملاحظات": e.description} for e in expenses]
    st.dataframe(pd.DataFrame(exp_data), use_container_width=True)

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

st.warning(f"### 🛡️ إجمالي العهد والمسؤولية: {total_resp:,.2f} ج.م")

if not is_closed:
    if st.button("🔒 إغلاق الوردية", type="primary", use_container_width=True):
        current_day.status = "CLOSED"
        current_day.closing_inside = curr_inside
        current_day.closing_cash_treasury = curr_cash_treasury
        current_day.closing_insta_treasury = curr_insta_treasury
        db.commit()
        st.success("تم إغلاق اليوم بنجاح وتجميد الأرصدة!")
        st.rerun()

db.close()