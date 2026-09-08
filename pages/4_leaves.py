import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_db
from database.models import Employee, Leave, Region

# كود CSS مخصص للموبايل
st.markdown("""
<style>
    @media (max-width: 768px) {
        .stButton>button { min-height: 44px !important; font-size: 15px !important; }
        input, select, div[data-baseweb="select"] { min-height: 45px !important; font-size: 16px !important; }
    }
</style>
""", unsafe_allow_html=True)

if 'current_region_id' not in st.session_state:
    st.warning("الرجاء اختيار المنطقة من الصفحة الرئيسية أولاً.")
    st.stop()

region_id = st.session_state['current_region_id']
region_name = st.session_state['current_region_name']
db = next(get_db())

st.title("🏖️ سجل إجازات الشركة (الشروق & مدينتي)")
st.caption(f"الفرع الحالي: {region_name} (الإجازات المسجلة تظهر لجميع الفروع)")
st.markdown("---")

# خريطة بأسماء الفروع لعرضها في السجل
regions = db.query(Region).all()
region_map = {r.id: r.name for r in regions}

# ==========================================
# 1. نموذج تسجيل إجازة جديدة
# ==========================================
st.subheader("➕ تسجيل إجازة موظف")

# جلب كل موظفي الشركة النشطين
employees = db.query(Employee).filter(Employee.is_active == True).all()
emp_names = sorted(list(set([e.name for e in employees]))) if employees else []

if emp_names:
    with st.form("add_leave_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            l_emp = st.selectbox("اختر الموظف 👤", emp_names)
            l_date = st.date_input("تاريخ الإجازة 📅", date.today())
        with col2:
            l_notes = st.text_input("نوع / سبب الإجازة (مثل: أسبوعية، عارضة، مرضي) 📝")
            
        if st.form_submit_button("تسجيل الإجازة 💾", type="primary", use_container_width=True):
            new_leave = Leave(
                region_id=region_id,
                employee_name=l_emp,
                leave_date=l_date,
                notes=l_notes.strip() if l_notes else "إجازة"
            )
            db.add(new_leave)
            db.commit()
            st.success(f"✅ تم تسجيل إجازة للموظف {l_emp} بتاريخ {l_date} (ستظهر في كل الفروع)!")
            st.rerun()
else:
    st.info("لا يوجد موظفين مضافين. أضف موظفين من صفحة الإعدادات أولاً.")

st.markdown("---")

# ==========================================
# 2. عرض سجل إجازات الشركة العام
# ==========================================
st.subheader("📋 كشف إجازات موظفي الشركة")

# جلب كل إجازات الشركة بدون حظر المنطقة
leaves = db.query(Leave).order_by(Leave.leave_date.desc()).all()

if leaves:
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        filter_emp = st.selectbox("🔍 تصفية حسب الموظف:", ["كل الموظفين"] + emp_names)
    with c_f2:
        filter_reg = st.selectbox("🔍 تصفية حسب الفرع:", ["كل الفروع"] + list(region_map.values()))
        
    filtered_leaves = leaves
    if filter_emp != "كل الموظفين":
        filtered_leaves = [l for l in filtered_leaves if l.employee_name == filter_emp]
    if filter_reg != "كل الفروع":
        filtered_leaves = [l for l in filtered_leaves if region_map.get(l.region_id) == filter_reg]
        
    st.write(f"##### عدد الإجازات: {len(filtered_leaves)}")
    for l in filtered_leaves:
        branch_registered = region_map.get(l.region_id, "غير محدد")
        c1, c2, c3 = st.columns([3, 3, 1])
        c1.write(f"📅 **{l.leave_date.strftime('%Y-%m-%d')}** | 👤 {l.employee_name}")
        c2.write(f"📍 فرع: {branch_registered} | 📝 {l.notes or 'إجازة'}")
        if c3.button("❌", key=f"del_leave_{l.id}"):
            db.delete(l)
            db.commit()
            st.rerun()
        st.divider()
else:
    st.info("لم يتم تسجيل أي إجازات حتى الآن في أي فرع.")

db.close()
