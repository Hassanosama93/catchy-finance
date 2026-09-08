import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_db
from database.models import Order, Expense, BusinessDay, PaymentMethod, ExpenseSource, Employee
from sqlalchemy import func

# كود CSS مخصص للموبايل
st.markdown("""
<style>
    @media (max-width: 768px) {
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

st.title(f"📊 التقارير المالية والإدارية - {st.session_state['current_region_name']}")
st.markdown("---")

# فلتر المدة
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
# 1. إجمالي الإيرادات (تشمل الاشتراكات والطلبات)
# ==========================================
st.subheader("💰 إجمالي الإيرادات في الفترة")

# تم إزالة شرط استبعاد الاشتراكات لجمع كل المبالغ
orders = db.query(Order).filter(Order.business_day_id.in_(day_ids))
cash_revenue_period = orders.filter(Order.payment_method == PaymentMethod.cash).with_entities(func.sum(Order.price)).scalar() or 0.0
insta_revenue_period = orders.filter(Order.payment_method == PaymentMethod.insta).with_entities(func.sum(Order.price)).scalar() or 0.0
total_revenue_period = cash_revenue_period + insta_revenue_period

r1, r2, r3 = st.columns(3)
r1.metric("كاش (المضاف للداخل)", f"{cash_revenue_period:,.2f} ج.م")
r2.metric("انستا الطلبات", f"{insta_revenue_period:,.2f} ج.م")
r3.metric("إجمالي الإيرادات", f"{total_revenue_period:,.2f} ج.م")

st.markdown("---")

# ==========================================
# 2. كشف حساب الموظفين (مع فلتر بالموظف والتاريخ)
# ==========================================
st.subheader("👨‍🔧 كشف حساب الموظفين (السلف والمصروفات)")

expenses_period = db.query(Expense).filter(Expense.business_day_id.in_(day_ids)).all()

if expenses_period:
    exp_list = [{
        "التاريخ": e.business_day.business_date.strftime("%Y-%m-%d"),
        "الموظف": e.person_entity,
        "نوع الخارج": e.expense_type,
        "المبلغ": float(e.amount),
        "المصدر": e.source.value,
        "ملاحظات": e.description or ""
    } for e in expenses_period]
    
    df_exp = pd.DataFrame(exp_list)
    
    # قائمة بأسماء الموظفين للفلترة
    all_emp_names = sorted(list(df_exp["الموظف"].unique()))
    selected_emp = st.selectbox("🔍 اختر الموظف لعرض كشف حسابه بالتفصيل:", ["عرض مجمع لكل الموظفين"] + all_emp_names)
    
    if selected_emp == "عرض مجمع لكل الموظفين":
        pivot_emp = df_exp.pivot_table(index='الموظف', columns='نوع الخارج', values='المبلغ', aggfunc='sum', fill_value=0.0)
        pivot_emp['إجمالي المسحوبات'] = pivot_emp.sum(axis=1)
        st.dataframe(pivot_emp, use_container_width=True)
    else:
        # تصفية حسب الموظف المختار
        emp_df = df_exp[df_exp["الموظف"] == selected_emp]
        emp_total = emp_df["المبلغ"].sum()
        
        st.success(f"💼 إجمالي ما استلمه **{selected_emp}** في هذه الفترة: **{emp_total:,.2f} ج.م**")
        
        # جدول تفصيلي بحركات الموظف وتواريخها
        st.write(f"##### تفاصيل مسحوبات {selected_emp} بالتاريخ والسبب:")
        st.dataframe(
            emp_df[["التاريخ", "نوع الخارج", "المبلغ", "المصدر", "ملاحظات"]],
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("لا توجد مسحوبات أو سلف للموظفين في هذه الفترة.")

st.markdown("---")

# ==========================================
# 3. تحليل بنود المصروفات العامة (بنزين، سكن...)
# ==========================================
st.subheader("💸 أين ذهبت المصروفات؟ (إجمالي البنود)")

if expenses_period:
    total_expenses_period = sum([float(e.amount) for e in expenses_period])
    category_summary = df_exp.groupby("نوع الخارج")["المبلغ"].sum().reset_index()
    category_summary.columns = ["بند الخارج", "إجمالي المبلغ (ج.م)"]
    category_summary = category_summary.sort_values(by="إجمالي المبلغ (ج.م)", ascending=False)
    
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        st.dataframe(category_summary, use_container_width=True, hide_index=True)
    with col_t2:
        st.metric("إجمالي المنصرف", f"{total_expenses_period:,.2f} ج.م")

st.markdown("---")

# ==========================================
# 4. مصادر خروج الأموال (الداخل والعهد)
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
