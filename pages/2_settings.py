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

# 1. إدارة الموظفين (إضافة وحذف)
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
        st.write("##### الموظفين الحاليين (يمكنك حذف أي موظف):")
        for emp in employees:
            col_e1, col_e2 = st.columns([3, 1])
            col_e1.write(f"👤 {emp.name}")
            if col_e2.button("حذف ❌", key=f"del_emp_{emp.id}"):
                db.delete(emp)
                db.commit()
                st.rerun()

# 2. إدارة أنواع الخارج (إضافة وحذف)
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

# 3. تعديل أرصدة البداية (الداخل والعهد)
with tab3:
    st.subheader("ضبط رصيد البداية وتغذية العهد")
    st.caption("الداخل: هو رصيد كاش الأوردرات التراكمي. العهدة: مبالغ خارجية مستقلة تماماً.")
    
    today = date.today()
    current_day = db.query(BusinessDay).filter(BusinessDay.region_id == region_id, BusinessDay.business_date == today).first()
    
    if current_day:
        st.write(f"##### تعديل رصيد بداية اليوم لـ (الداخل) ليوم: {today}")
        new_inside = st.number_input("رصيد الداخل الافتتاحي (ج.م)", value=float(current_day.opening_inside or 0.0), step=50.0)
        if st.button("تحديث رصيد الداخل 💾"):
            current_day.opening_inside = new_inside
            db.commit()
            st.success("تم تحديث رصيد بداية الداخل بنجاح!")
            st.rerun()
            
        st.markdown("---")
        st.write("##### إضافة عهدة جديدة (كاش أو انستا):")
        with st.form("treasury_feed_form"):
            t_type = st.selectbox("نوع العهدة", ["عهدة Cash", "عهدة Insta"])
            t_amt = st.number_input("المبلغ المضاف للعهدة", min_value=1.0, step=100.0)
            t_desc = st.text_input("البيان", value="تغذية عهدة")
            if st.form_submit_button("إضافة إلى العهدة 💰"):
                tt_enum = TreasuryType.cash if t_type == "عهدة Cash" else TreasuryType.insta
                db.add(TreasuryMovement(
                    business_day_id=current_day.id, treasury_type=tt_enum,
                    movement_type=MovementType.addition, amount=t_amt, description=t_desc
                ))
                db.commit()
                st.success(f"تمت إضافة {t_amt} إلى {t_type}")
                st.rerun()
    else:
        st.info("قم بفتح وردية اليوم أولاً من صفحة الوردية لتتمكن من تعديل أرصدة البداية.")

# 4. حذف وتصفير الأيام
with tab4:
    st.subheader("⚠️ حذف وردية يوم بالكامل")
    st.warning("تحذير: سيتم حذف اليوم بجميع طلباته ومصروفاته نهائياً من قاعدة البيانات!")
    
    all_days = db.query(BusinessDay).filter(BusinessDay.region_id == region_id).order_by(BusinessDay.business_date.desc()).all()
    if all_days:
        day_dict = {f"{d.business_date} (الحالة: {d.status})": d.id for d in all_days}
        selected_day_label = st.selectbox("اختر اليوم الذي تريد حذفه:", list(day_dict.keys()))
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