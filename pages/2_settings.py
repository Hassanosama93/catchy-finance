import streamlit as st
import pandas as pd
from database.connection import get_db
from database.models import Employee, ExpenseCategory, Region, TreasuryMovement, TreasuryType, MovementType, BusinessDay, Order, Expense
from datetime import date

if 'current_region_id' not in st.session_state:
    st.warning("الرجاء اختيار المنطقة من الصفحة الرئيسية أولاً.")
    st.stop()

region_id = st.session_state['current_region_id']
region_name = st.session_state['current_region_name']
db = next(get_db())

st.title(f"⚙️ إعدادات وإدارة النظام - {region_name}")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["👨‍🔧 الموظفين", "💸 أنواع الخارج", "🏦 رصيد البداية والعهد", "🗑️ إدارة وحذف الأيام"])

# 1. إدارة الموظفين
with tab1:
    st.subheader("إضافة وحذف الموظفين")
    with st.form("add_emp_form", clear_on_submit=True):
        emp_name = st.text_input("اسم الموظف الجديد")
        if st.form_submit_button("إضافة موظف ➕"):
            if emp_name.strip():
                db.add(Employee(name=emp_name.strip(), region_id=region_id))
                db.commit()
                st.success(f"تمت إضافة الموظف {emp_name}")
                st.rerun()

    st.markdown("---")
    employees = db.query(Employee).filter(Employee.is_active == True).all()
    if employees:
        st.write("##### الموظفين الحاليين:")
        for emp in employees:
            col_e1, col_e2 = st.columns([3, 1])
            col_e1.write(f"👤 {emp.name}")
            if col_e2.button("حذف ❌", key=f"del_emp_{emp.id}"):
                db.delete(emp)
                db.commit()
                st.rerun()

# 2. إدارة أنواع الخارج
with tab2:
    st.subheader("إضافة وحذف بنود الخارج")
    with st.form("add_cat_form", clear_on_submit=True):
        cat_name = st.text_input("اسم البند (سلفة، تيبس، بنزين...)")
        if st.form_submit_button("إضافة البند ➕"):
            if cat_name.strip():
                db.add(ExpenseCategory(name=cat_name.strip()))
                db.commit()
                st.success("تمت الإضافة بنجاح")
                st.rerun()

    st.markdown("---")
    categories = db.query(ExpenseCategory).filter(ExpenseCategory.is_active == True).all()
    if categories:
        st.write("##### بنود الخارج المسجلة:")
        for cat in categories:
            col_c1, col_c2 = st.columns([3, 1])
            col_c1.write(f"🏷️ {cat.name}")
            if col_c2.button("حذف ❌", key=f"del_cat_{cat.id}"):
                db.delete(cat)
                db.commit()
                st.rerun()

# 3. تعديل أرصدة البداية وتغذية العهد (محدث وشامل)
with tab3:
    st.subheader("ضبط أرصدة البداية لأي يوم")
    st.caption("حدد تاريخ اليوم واكتب أرصدة البداية التي تريد بدء اليوم بها.")
    
    target_date = st.date_input("📅 اختر تاريخ اليوم المراد ضبط أرصدته:", date.today())
    
    target_day = db.query(BusinessDay).filter(
        BusinessDay.region_id == region_id,
        BusinessDay.business_date == target_date
    ).first()
    
    if not target_day:
        target_day = BusinessDay(
            region_id=region_id,
            business_date=target_date,
            status="OPEN",
            opening_inside=0.0,
            opening_cash_treasury=0.0,
            opening_insta_treasury=0.0
        )
        db.add(target_day)
        db.commit()
        
    with st.form("set_opening_balances_form"):
        st.write(f"##### أرصدة بداية يوم ({target_date}):")
        new_in = st.number_input("رصيد بداية (الداخل) 💵", value=float(target_day.opening_inside or 0.0), step=50.0)
        new_cash_tr = st.number_input("رصيد بداية (عهدة Cash) 🏦", value=float(target_day.opening_cash_treasury or 0.0), step=100.0)
        new_insta_tr = st.number_input("رصيد بداية (عهدة Insta) 📱", value=float(target_day.opening_insta_treasury or 0.0), step=100.0)
        
        if st.form_submit_button("حفظ وتحديث أرصدة البداية 💾", type="primary", use_container_width=True):
            target_day.opening_inside = new_in
            target_day.opening_cash_treasury = new_cash_tr
            target_day.opening_insta_treasury = new_insta_tr
            db.commit()
            st.success(f"✅ تم تحديث أرصدة بداية يوم {target_date} بنجاح! ستظهر فوراً في الوردية.")
            st.rerun()

# 4. حذف الأيام
with tab4:
    st.subheader("⚠️ حذف وردية يوم بالكامل")
    all_days = db.query(BusinessDay).filter(BusinessDay.region_id == region_id).order_by(BusinessDay.business_date.desc()).all()
    if all_days:
        day_dict = {f"{d.business_date} (الحالة: {d.status})": d.id for d in all_days}
        selected_day_label = st.selectbox("اختر اليوم:", list(day_dict.keys()))
        target_day_id = day_dict[selected_day_label]
        
        if st.button("تأكيد حذف اليوم بالكامل 🗑️", type="primary"):
            db.query(Order).filter(Order.business_day_id == target_day_id).delete()
            db.query(Expense).filter(Expense.business_day_id == target_day_id).delete()
            db.query(TreasuryMovement).filter(TreasuryMovement.business_day_id == target_day_id).delete()
            db.query(BusinessDay).filter(BusinessDay.id == target_day_id).delete()
            db.commit()
            st.success("تم مسح اليوم بنجاح!")
            st.rerun()

db.close()
