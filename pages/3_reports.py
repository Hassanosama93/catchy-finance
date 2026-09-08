import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_db
from database.models import Order, Expense, BusinessDay, PaymentMethod, ExpenseSource
from sqlalchemy import func

if 'current_region_id' not in st.session_state:
    st.warning("الرجاء اختيار المنطقة من الصفحة الرئيسية أولاً.")
    st.stop()

region_id = st.session_state['current_region_id']
db = next(get_db())

st.title(f"📊 التقارير المالية والإدارية - {st.session_state['current_region_name']}")
st.markdown("---")

col_f1, col_f2 = st.columns(2)
today = date.today()
with col_f1:
    start_date = st.date_input("من تاريخ", today.replace(day=1))
with col_f2:
    end_date = st.date_input("إلى تاريخ", today)

days = db.query(BusinessDay).filter(
    BusinessDay.region_id == region_id,
    BusinessDay.business_date >= start_date,
    BusinessDay.business_date <= end_date
).all()
day_ids = [d.id for d in days]

if not day_ids:
    st.info("لا توجد بيانات مسجلة في هذه الفترة.")
    st.stop()

# ==========================================
# 1. إجمالي الإيرادات (دخلنا كام؟)
# ==========================================
st.subheader("💰 إجمالي الإيرادات في الفترة")

orders = db.query(Order).filter(Order.business_day_id.in_(day_ids), Order.is_subscription == False)
cash_revenue_period = orders.filter(Order.payment_method == PaymentMethod.cash).with_entities(func.sum(Order.price)).scalar() or 0.0
insta_revenue_period = orders.filter(Order.payment_method == PaymentMethod.insta).with_entities(func.sum(Order.price)).scalar() or 0.0
total_revenue_period = cash_revenue_period + insta_revenue_period

expenses_period = db.query(Expense).filter(Expense.business_day_id.in_(day_ids)).all()
total_expenses_period = sum([float(e.amount) for e in expenses_period])

r1, r2, r3 = st.columns(3)
r1.metric("كاش الطلبات (دخل الداخل)", f"{cash_revenue_period:,.2f} ج.م")
r2.metric("انستا الطلبات", f"{insta_revenue_period:,.2f} ج.م")
r3.metric("إجمالي الإيرادات", f"{total_revenue_period:,.2f} ج.م")

st.markdown("---")

# ==========================================
# 2. تحليل المصروفات (صرفنا كام وعلى إيه مجمعاً؟)
# ==========================================
st.subheader("💸 أين ذهبت المصروفات؟ (إجمالي بنود الصرف)")

if expenses_period:
    exp_list = [{
        "الموظف": e.person_entity,
        "نوع الخارج": e.expense_type,
        "المبلغ": float(e.amount),
        "المصدر": e.source.value
    } for e in expenses_period]
    
    df_exp = pd.DataFrame(exp_list)
    
    # تجميع كل بند ومجموع ما صُرف عليه (بنزين، سكن، مشتريات...)
    category_summary = df_exp.groupby("نوع الخارج")["المبلغ"].sum().reset_index()
    category_summary.columns = ["بند الخارج", "إجمالي المبلغ المنصرف (ج.م)"]
    category_summary = category_summary.sort_values(by="إجمالي المبلغ المنصرف (ج.م)", ascending=False)
    
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        st.dataframe(category_summary, use_container_width=True, hide_index=True)
    with col_t2:
        st.metric("إجمالي ما تم صرفه", f"{total_expenses_period:,.2f} ج.م")
        st.caption("مجموع كل ما خرج سواء من الداخل أو من العهد الخارجية.")
else:
    st.info("لا توجد مصاريف مسجلة في هذه الفترة.")

st.markdown("---")

# ==========================================
# 3. كشف حساب الموظفين (سلف، تيبس، مسحوبات شهرية)
# ==========================================
st.subheader("👨‍🔧 كشف حساب الموظفين (لتسوية الرواتب)")

if expenses_period:
    pivot_emp = df_exp.pivot_table(index='الموظف', columns='نوع الخارج', values='المبلغ', aggfunc='sum', fill_value=0.0)
    pivot_emp['إجمالي ما تم سحبه'] = pivot_emp.sum(axis=1)
    
    st.dataframe(pivot_emp, use_container_width=True)
    st.caption("💡 هذا الجدول يوضح لك بالتفصيل كل موظف أخذ كام من كل بند خلال الشهر لخصم السلف من مرتبه وتصفية حسابه.")

st.markdown("---")

# ==========================================
# 4. تفاصيل مصادر الصرف (خرجوا منين؟)
# ==========================================
st.subheader("🏦 مصادر خروج المصروفات")
if expenses_period:
    inside_exp = df_exp[df_exp["المصدر"] == ExpenseSource.inside.value]["المبلغ"].sum()
    cash_tr_exp = df_exp[df_exp["المصدر"] == ExpenseSource.cash_treasury.value]["المبلغ"].sum()
    insta_tr_exp = df_exp[df_exp["المصدر"] == ExpenseSource.insta_treasury.value]["المبلغ"].sum()
    
    s1, s2, s3 = st.columns(3)
    s1.metric("خرج من (الداخل)", f"{inside_exp:,.2f} ج.م")
    s2.metric("خرج من (عهدة كاش)", f"{cash_tr_exp:,.2f} ج.م")
    s3.metric("خرج من (عهدة انستا)", f"{insta_tr_exp:,.2f} ج.م")

db.close()