import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_db
from database.models import Order, Expense, BusinessDay, PaymentMethod, ExpenseSource, Region
from sqlalchemy import func

# كود CSS قاطع يمنع نزول الكروت تحت بعضها ويخفي السهم المشوه
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');
    * { font-family: 'Tajawal', sans-serif !important; }
    
    /* إخفاء أي أزرار أو أسهم للقائمة الجانبية نهائياً */
    [data-testid="collapsedControl"], button[kind="header"], #MainMenu, header { display: none !important; }
    
    .block-container { padding: 1rem 0.6rem 3rem 0.6rem !important; }
    
    /* إجبار الأعمدة على البقاء في سطر واحد أفقي للموبايل */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 6px !important;
    }
    [data-testid="stHorizontalBlock"] > div {
        flex: 1 1 0px !important;
        min-width: 0 !important;
    }
    
    /* تجميل وضغط الكروت */
    div[data-testid="metric-container"] {
        background: #181c24;
        border: 1px solid #2d3748;
        padding: 8px 4px !important;
        border-radius: 10px !important;
        text-align: center !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 17px !important;
        font-weight: 800 !important;
        color: #00d2ff !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 11px !important;
        color: #a0aec0 !important;
        white-space: nowrap !important;
    }
</style>
""", unsafe_allow_html=True)

db = next(get_db())

# شريط علوي أنيق
rep_c1, rep_c2 = st.columns([3, 1])
rep_c1.markdown("<h4 style='margin:0; color:#00d2ff;'>📊 التقارير المالية</h4>", unsafe_allow_html=True)
if rep_c2.button("🏠 الرئيسية", use_container_width=True): st.switch_page("app.py")

# ==========================================
# 1. فلتر النطاق والفترة
# ==========================================
col_scope, col_f1, col_f2 = st.columns([2, 1, 1])

regions = db.query(Region).filter(Region.is_active == True).all()
region_dict = {r.name: r.id for r in regions}
scope_options = ["🌐 الشركة مجمعة (كل الفروع)"] + [f"🏢 {r.name}" for r in regions]

with col_scope:
    selected_scope = st.selectbox("📍 النطاق:", scope_options)

today = date.today()
with col_f1: start_date = st.date_input("من", today.replace(day=1))
with col_f2: end_date = st.date_input("إلى", today)

days_query = db.query(BusinessDay).filter(
    BusinessDay.business_date >= start_date,
    BusinessDay.business_date <= end_date
)

if selected_scope != "🌐 الشركة مجمعة (كل الفروع)":
    chosen_reg_name = selected_scope.replace("🏢 ", "")
    days_query = days_query.filter(BusinessDay.region_id == region_dict[chosen_reg_name])

days = days_query.all()
day_ids = [d.id for d in days]

if not day_ids:
    st.info("لا توجد بيانات مسجلة في هذه الفترة.")
    st.stop()

day_info_map = {d.id: {"date": d.business_date.strftime("%Y-%m-%d"), "region": d.region_id} for d in days}
region_id_to_name = {r.id: r.name for r in regions}

# ==========================================
# 2. ملخص الإيرادات
# ==========================================
st.caption("💰 الإيرادات المحصلة:")

orders = db.query(Order).filter(Order.business_day_id.in_(day_ids))

# تحويل مباشر لـ float لتجنب TypeError نهائياً
cash_rev_total = float(orders.filter(Order.payment_method == PaymentMethod.cash).with_entities(func.sum(Order.price)).scalar() or 0)
insta_rev_total = float(orders.filter(Order.payment_method == PaymentMethod.insta).with_entities(func.sum(Order.price)).scalar() or 0)
grand_total_rev = cash_rev_total + insta_rev_total

r1, r2, r3 = st.columns(3)
r1.metric("كاش الطلبات", f"{int(cash_rev_total):,}")
r2.metric("انستا الطلبات", f"{int(insta_rev_total):,}")
r3.metric("الإجمالي", f"{int(grand_total_rev):,}")

# مقارنة بين الفروع لو التقرير مجمع (مع حل الخطأ)
if selected_scope == "🌐 الشركة مجمعة (كل الفروع)" and len(regions) > 1:
    st.write("##### 📌 مقارنة إيرادات الفروع:")
    branch_rev_data = []
    for r in regions:
        r_days = [d.id for d in days if d.region_id == r.id]
        if r_days:
            r_orders = db.query(Order).filter(Order.business_day_id.in_(r_days))
            c_r = float(r_orders.filter(Order.payment_method == PaymentMethod.cash).with_entities(func.sum(Order.price)).scalar() or 0)
            i_r = float(r_orders.filter(Order.payment_method == PaymentMethod.insta).with_entities(func.sum(Order.price)).scalar() or 0)
            branch_rev_data.append({"الفرع": r.name, "كاش": int(c_r), "انستا": int(i_r), "الإجمالي": int(c_r + i_r)})
    if branch_rev_data:
        st.dataframe(pd.DataFrame(branch_rev_data), use_container_width=True, hide_index=True)

# ==========================================
# 3. قسم تسوية الرواتب (سلف ومصروفات فقط)
# ==========================================
st.markdown("---")
st.subheader("👨‍🔧 كشف تسوية الرواتب (يُخصم من المرتب)")
st.caption("⚠️ يشمل السلف والمصروفات الشخصية فقط. (بنزين العمل ومصاريف التشغيل مفصولة بالأسفل)")

expenses_period = db.query(Expense).filter(Expense.business_day_id.in_(day_ids)).all()

if expenses_period:
    exp_records = []
    for e in expenses_period:
        d_info = day_info_map.get(e.business_day_id, {"date": "غير محدد", "region": 0})
        exp_records.append({
            "التاريخ": d_info["date"],
            "الفرع": region_id_to_name.get(d_info["region"], "عام"),
            "الموظف": e.person_entity,
            "نوع الخارج": e.expense_type,
            "المبلغ": float(e.amount),
            "المصدر": e.source.value,
            "ملاحظات": e.description or ""
        })
    df_all_exp = pd.DataFrame(exp_records)
    
    def is_deductible(exp_type):
        t = str(exp_type).strip()
        return ("سلف" in t) or ("مصروف" in t and "بنزين" not in t and "سكن" not in t)
    
    df_deductions = df_all_exp[df_all_exp["نوع الخارج"].apply(is_deductible)]
    df_operations = df_all_exp[~df_all_exp["نوع الخارج"].apply(is_deductible)]
    
    if not df_deductions.empty:
        salary_pivot = df_deductions.pivot_table(
            index="الموظف", columns="الفرع", values="المبلغ", aggfunc="sum", fill_value=0
        )
        salary_pivot["🔴 إجمالي الخصم من الراتب"] = salary_pivot.sum(axis=1).astype(int)
        st.dataframe(salary_pivot, use_container_width=True)
    else:
        st.info("لا توجد أي سلف أو مسحوبات شخصية في هذه الفترة.")
        
    all_emp_names = sorted(list(df_all_exp["الموظف"].unique()))
    chosen_emp = st.selectbox("🔍 تفاصيل حساب موظف محدد:", ["-- اختر موظفاً --"] + all_emp_names)
    
    if chosen_emp != "-- اختر موظفاً --":
        emp_records = df_all_exp[df_all_exp["الموظف"] == chosen_emp]
        emp_ded = emp_records[emp_records["نوع الخارج"].apply(is_deductible)]["المبلغ"].sum()
        emp_opex = emp_records[~emp_records["نوع الخارج"].apply(is_deductible)]["المبلغ"].sum()
        
        c_e1, c_e2 = st.columns(2)
        c_e1.error(f"🔴 يُخصم من راتبه (سلف): **{int(emp_ded):,} ج.م**")
        c_e2.info(f"🔵 استلمها للشغل (بنزين/تشغيل): **{int(emp_opex):,} ج.م**")
        
        st.write(f"##### سجل حركات {chosen_emp}:")
        st.dataframe(emp_records[["التاريخ", "الفرع", "نوع الخارج", "المبلغ", "المصدر", "ملاحظات"]], use_container_width=True, hide_index=True)

# ==========================================
# 4. مصاريف تشغيل الشركة (OPEX - لا تخصم من العامل)
# ==========================================
st.markdown("---")
st.subheader("⛽ مصاريف تشغيل الشركة (بنزين، خامات، سكن...)")

if expenses_period and not df_operations.empty:
    opex_summary = df_operations.groupby("نوع الخارج")["المبلغ"].sum().reset_index()
    opex_summary.columns = ["بند التشغيل", "إجمالي المبلغ"]
    opex_summary["إجمالي المبلغ"] = opex_summary["إجمالي المبلغ"].astype(int)
    opex_summary = opex_summary.sort_values(by="إجمالي المبلغ", ascending=False)
    
    co1, co2 = st.columns([2, 1])
    with co1: st.dataframe(opex_summary, use_container_width=True, hide_index=True)
    with co2: st.metric("إجمالي مصاريف التشغيل", f"{int(df_operations['المبلغ'].sum()):,}")

# ==========================================
# 5. مصادر خروج النقدية
# ==========================================
st.markdown("---")
st.caption("🏦 مصادر خروج النقدية في الفترة:")
if expenses_period:
    in_exp = float(df_all_exp[df_all_exp["المصدر"] == ExpenseSource.inside.value]["المبلغ"].sum())
    c_tr_exp = float(df_all_exp[df_all_exp["المصدر"] == ExpenseSource.cash_treasury.value]["المبلغ"].sum())
    i_tr_exp = float(df_all_exp[df_all_exp["المصدر"] == ExpenseSource.insta_treasury.value]["المبلغ"].sum())
    
    s1, s2, s3 = st.columns(3)
    s1.metric("من (الداخل)", f"{int(in_exp):,}")
    s2.metric("من (عهدة كاش)", f"{int(c_tr_exp):,}")
    s3.metric("من (عهدة انستا)", f"{int(i_tr_exp):,}")

db.close()
