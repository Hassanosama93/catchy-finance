import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database.connection import get_db
from database.models import Order, Expense, PaymentMethod, ExpenseSource, BusinessDay, Employee, ExpenseCategory, TreasuryMovement, TreasuryType, MovementType
from services.calculations import (
    calculate_cash_revenue, calculate_insta_revenue, calculate_total_revenue,
    calculate_expenses_by_source, calculate_inside_balance,
    calculate_cash_treasury_balance, calculate_insta_treasury_balance,
    calculate_total_responsibility, calculate_treasury_net_movements
)

# كود CSS مخصص للموبايل
st.markdown("""
<style>
    @media (max-width: 768px) {
        .stButton>button { min-height: 44px !important; font-size: 15px !important; }
        input, select, div[data-baseweb="select"] { min-height: 45px !important; font-size: 16px !important; }
        div[data-testid="column"] { flex: 1 1 calc(50% - 10px) !important; min-width: 130px !important; }
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

# جلب أو إنشاء اليوم
current_day = db.query(BusinessDay).filter(
    BusinessDay.region_id == region_id, BusinessDay.business_date == selected_date
).first()

prev_closed_day = db.query(BusinessDay).filter(
    BusinessDay.region_id == region_id,
    BusinessDay.business_date < selected_date,
    BusinessDay.status == "CLOSED"
).order_by(BusinessDay.business_date.desc()).first()

if not current_day:
    current_day = BusinessDay(
        region_id=region_id, business_date=selected_date, status="OPEN",
        opening_inside=prev_closed_day.closing_inside if prev_closed_day else 0.0,
        opening_cash_treasury=prev_closed_day.closing_cash_treasury if prev_closed_day else 0.0,
        opening_insta_treasury=prev_closed_day.closing_insta_treasury if prev_closed_day else 0.0
    )
    db.add(current_day)
    db.commit()

is_closed = (current_day.status == "CLOSED")

if is_closed:
    st.info("🔒 هذه الوردية مغلقة حالياً. (يمكنك إعادة فتحها للتعديل من زر أسفل الصفحة)")

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
# 2. قسم الطلبات
# ==========================================
st.subheader("📋 الطلبات")

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

if not is_closed:
    with st.expander("➕ إضافة طلب جديد", expanded=True):
        with st.form("quick_order_form", clear_on_submit=True):
            o_col1, o_col2 = st.columns(2)
            with o_col1:
                o_time = st.selectbox("الوقت ⏰", time_slots)
                o_name = st.text_input("اسم العميل 👤")
                o_sub = st.checkbox("☑️ اشتراك")
            with o_col2:
                o_price_input = st.number_input("السعر (ج.م) 💵", min_value=0, value=None, step=10, placeholder="اكتب السعر...")
                o_pay = st.selectbox("طريقة الدفع 💳", ["None", "Cash", "Insta"])
                o_notes = st.text_input("ملاحظات 📝")
                
            if st.form_submit_button("حفظ الطلب 💾", type="primary", use_container_width=True):
                pm = PaymentMethod.none
                if o_pay == "Cash": pm = PaymentMethod.cash
                elif o_pay == "Insta": pm = PaymentMethod.insta
                
                o_price = float(o_price_input) if o_price_input is not None else 0.0
                real_price = o_price if pm != PaymentMethod.none else 0.0
                    
                db.add(Order(
                    business_day_id=current_day.id,
                    order_time=o_time,
                    customer_name=o_name.strip() if o_name else "بدون اسم",
                    is_subscription=o_sub,
                    price=real_price,
                    payment_method=pm,
                    notes=o_notes
                ))
                db.commit()
                st.success("تم حفظ الطلب بنجاح!")
                st.rerun()

orders = db.query(Order).filter(Order.business_day_id == current_day.id).all()
orders.sort(key=lambda o: time_slots.index(o.order_time) if o.order_time in time_slots else 999)

if orders:
    st.write(f"##### الطلبات المسجلة ({len(orders)} طلب):")
    for o in orders:
        c_ord1, c_ord2, c_ord3, c_ord4 = st.columns([3, 3, 1, 1])
        c_ord1.write(f"⏰ **{o.order_time}** | 👤 {o.customer_name} {'(اشتراك)' if o.is_subscription else ''}")
        if o.notes and o.notes.strip():
            c_ord1.caption(f"📝 {o.notes.strip()}")
            
        c_ord2.write(f"💰 {o.price:,.2f} ج.م ({o.payment_method.value})")
        
        if not is_closed:
            if c_ord3.button("✏️", key=f"edit_btn_{o.id}"):
                st.session_state['editing_order_id'] = o.id
                st.rerun()
            if c_ord4.button("❌", key=f"del_ord_{o.id}"):
                db.delete(o)
                db.commit()
                st.rerun()

        if st.session_state.get('editing_order_id') == o.id:
            with st.form(f"edit_form_{o.id}"):
                st.info(f"تعديل طلب: {o.customer_name}")
                ed_c1, ed_c2 = st.columns(2)
                with ed_c1:
                    time_idx = time_slots.index(o.order_time) if o.order_time in time_slots else 0
                    new_time = st.selectbox("الوقت", time_slots, index=time_idx)
                    new_name = st.text_input("اسم العميل", value=o.customer_name)
                    new_sub = st.checkbox("اشتراك", value=o.is_subscription)
                with ed_c2:
                    new_price = st.number_input("السعر", min_value=0, value=int(o.price), step=10)
                    pay_options = ["None", "Cash", "Insta"]
                    pay_idx = pay_options.index(o.payment_method.value) if o.payment_method.value in pay_options else 0
                    new_pay = st.selectbox("طريقة الدفع", pay_options, index=pay_idx)
                    new_notes = st.text_input("ملاحظات", value=o.notes or "")
                    
                col_save, col_cancel = st.columns(2)
                if col_save.form_submit_button("حفظ التعديل ✅", use_container_width=True):
                    pm = PaymentMethod.none
                    if new_pay == "Cash": pm = PaymentMethod.cash
                    elif new_pay == "Insta": pm = PaymentMethod.insta
                    
                    o.order_time = new_time
                    o.customer_name = new_name.strip() if new_name else "بدون اسم"
                    o.is_subscription = new_sub
                    o.price = float(new_price) if pm != PaymentMethod.none else 0.0
                    o.payment_method = pm
                    o.notes = new_notes
                    db.commit()
                    del st.session_state['editing_order_id']
                    st.success("تم تحديث الطلب بنجاح!")
                    st.rerun()
                    
                if col_cancel.form_submit_button("إلغاء ↩️", use_container_width=True):
                    del st.session_state['editing_order_id']
                    st.rerun()
                    
        st.divider()
else:
    st.info("لا توجد طلبات مسجلة اليوم حتى الآن.")

st.markdown("---")

# ==========================================
# 3. إدارة الخارج ومربعات التجميع مع إمكانية التعديل
# ==========================================
st.subheader("💸 الخارج")

exp_inside = calculate_expenses_by_source(db, current_day.id, ExpenseSource.inside)
exp_cash = calculate_expenses_by_source(db, current_day.id, ExpenseSource.cash_treasury)
exp_insta = calculate_expenses_by_source(db, current_day.id, ExpenseSource.insta_treasury)
total_exp = exp_inside + exp_cash + exp_insta

ex_col1, ex_col2, ex_col3, ex_col4 = st.columns(4)
ex_col1.metric("🔴 إجمالي الخارج", f"{total_exp:,.2f} ج.م")
ex_col2.metric("من الداخل", f"{exp_inside:,.2f} ج.م")
ex_col3.metric("من عهدة كاش", f"{exp_cash:,.2f} ج.م")
ex_col4.metric("من عهدة انستا", f"{exp_insta:,.2f} ج.م")

employees = db.query(Employee).filter(Employee.is_active == True).all()
emp_names = [e.name for e in employees] if employees else ["بدون موظف"]

categories = db.query(ExpenseCategory).filter(ExpenseCategory.is_active == True).all()
cat_names = [c.name for c in categories] if categories else ["عام"]

if not is_closed:
    with st.expander("➕ إضافة خارج جديد", expanded=False):
        with st.form("expense_form", clear_on_submit=True):
            ec1, ec2 = st.columns(2)
            with ec1:
                expense_emp = st.selectbox("الموظف / الشخص", emp_names)
                expense_type = st.selectbox("نوع الخارج", cat_names)
                exp_amt_input = st.number_input("المبلغ", min_value=0, value=None, step=10, placeholder="اكتب المبلغ...")
            with ec2:
                expense_source = st.selectbox("يُخصم من", ["الداخل", "عهدة كاش", "عهدة انستا"])
                expense_notes = st.text_area("تفاصيل / ملاحظات")
                
            if st.form_submit_button("تسجيل الخارج ⬇️", use_container_width=True):
                exp_amt = float(exp_amt_input) if exp_amt_input is not None else 0.0
                if exp_amt > 0:
                    src = ExpenseSource.inside
                    if expense_source == "عهدة كاش": src = ExpenseSource.cash_treasury
                    elif expense_source == "عهدة انستا": src = ExpenseSource.insta_treasury
                    
                    db.add(Expense(
                        business_day_id=current_day.id, person_entity=expense_emp, expense_type=expense_type,
                        amount=exp_amt, source=src, description=expense_notes
                    ))
                    db.commit()
                    st.rerun()

expenses = db.query(Expense).filter(Expense.business_day_id == current_day.id).all()
if expenses:
    for e in expenses:
        col_ex1, col_ex2, col_ex3, col_ex4 = st.columns([3, 3, 1, 1])
        col_ex1.write(f"👤 **{e.person_entity}** ({e.expense_type})")
        if e.description and e.description.strip():
            col_ex1.caption(f"📝 {e.description.strip()}")
            
        col_ex2.write(f"💸 {e.amount:,.2f} ج.م من ({e.source.value})")
        
        # أزرار التعديل والحذف للخارج
        if not is_closed:
            if col_ex3.button("✏️", key=f"edit_exp_btn_{e.id}"):
                st.session_state['editing_expense_id'] = e.id
                st.rerun()
            if col_ex4.button("❌", key=f"del_exp_btn_{e.id}"):
                db.delete(e)
                db.commit()
                st.rerun()

        # نافذة تعديل المصروف
        if st.session_state.get('editing_expense_id') == e.id:
            with st.form(f"edit_exp_form_{e.id}"):
                st.info(f"تعديل خارج: {e.person_entity} ({e.expense_type})")
                ee_c1, ee_c2 = st.columns(2)
                with ee_c1:
                    emp_idx = emp_names.index(e.person_entity) if e.person_entity in emp_names else 0
                    new_emp = st.selectbox("الموظف", emp_names, index=emp_idx)
                    cat_idx = cat_names.index(e.expense_type) if e.expense_type in cat_names else 0
                    new_cat = st.selectbox("نوع الخارج", cat_names, index=cat_idx)
                    new_amt = st.number_input("المبلغ", min_value=0.0, value=float(e.amount), step=10.0)
                with ee_c2:
                    sources = ["الداخل", "عهدة كاش", "عهدة انستا"]
                    src_idx = sources.index(e.source.value) if e.source.value in sources else 0
                    new_src_str = st.selectbox("يُخصم من", sources, index=src_idx)
                    new_notes = st.text_area("تفاصيل / ملاحظات", value=e.description or "")
                    
                col_save_exp, col_cancel_exp = st.columns(2)
                if col_save_exp.form_submit_button("حفظ التعديل ✅", use_container_width=True):
                    src_enum = ExpenseSource.inside
                    if new_src_str == "عهدة كاش": src_enum = ExpenseSource.cash_treasury
                    elif new_src_str == "عهدة انستا": src_enum = ExpenseSource.insta_treasury
                    
                    e.person_entity = new_emp
                    e.expense_type = new_cat
                    e.amount = new_amt
                    e.source = src_enum
                    e.description = new_notes
                    db.commit()
                    del st.session_state['editing_expense_id']
                    st.success("تم تحديث الخارج بنجاح!")
                    st.rerun()
                    
                if col_cancel_exp.form_submit_button("إلغاء ↩️", use_container_width=True):
                    del st.session_state['editing_expense_id']
                    st.rerun()

        st.divider()

st.markdown("---")

# ==========================================
# 4. تغذية العهدة المباشرة في الوردية
# ==========================================
if not is_closed:
    with st.expander("🏦 ➕ إضافة تغذية للعهدة في هذه الوردية (كاش أو انستا)", expanded=False):
        with st.form("quick_treasury_feed"):
            tf_col1, tf_col2 = st.columns(2)
            with tf_col1:
                feed_type = st.selectbox("نوع العهدة المضافة", ["عهدة Cash", "عهدة Insta"])
                feed_amt = st.number_input("المبلغ المضاف للعهدة", min_value=1.0, step=100.0)
            with tf_col2:
                feed_desc = st.text_input("بيان التغذية", value="تغذية عهدة للفرع")
                
            if st.form_submit_button("إضافة المبلغ للعهدة 💰", use_container_width=True):
                tt_enum = TreasuryType.cash if feed_type == "عهدة Cash" else TreasuryType.insta
                db.add(TreasuryMovement(
                    business_day_id=current_day.id, treasury_type=tt_enum,
                    movement_type=MovementType.addition, amount=feed_amt, description=feed_desc
                ))
                db.commit()
                st.success(f"✅ تمت إضافة {feed_amt:,.2f} إلى {feed_type} بنجاح!")
                st.rerun()

st.markdown("---")

# ==========================================
# 5. رصيد نهاية اليوم وإغلاق/إعادة فتح الوردية
# ==========================================
st.subheader("📊 رصيد نهاية اليوم")

curr_inside = calculate_inside_balance(db, current_day.id)
curr_cash_treasury = calculate_cash_treasury_balance(db, current_day.id)
curr_insta_treasury = calculate_insta_treasury_balance(db, current_day.id)
total_resp = calculate_total_responsibility(db, current_day.id)

cash_additions = calculate_treasury_net_movements(db, current_day.id, TreasuryType.cash)
insta_additions = calculate_treasury_net_movements(db, current_day.id, TreasuryType.insta)

rc1, rc2, rc3 = st.columns(3)
rc1.info(f"**داخل:** {curr_inside:,.2f} ج.م")
rc2.info(f"**عهدة كاش:** {curr_cash_treasury:,.2f} ج.م" + (f" (+{cash_additions} تغذية)" if cash_additions > 0 else ""))
rc3.info(f"**عهدة انستا:** {curr_insta_treasury:,.2f} ج.م" + (f" (+{insta_additions} تغذية)" if insta_additions > 0 else ""))

st.warning(f"### 🛡️ إجمالي العهد والمسؤولية: {total_resp:,.2f} ج.م")

if not is_closed:
    if st.button("🔒 إغلاق الوردية (تجميد الحسابات)", type="primary", use_container_width=True):
        current_day.status = "CLOSED"
        current_day.closing_inside = curr_inside
        current_day.closing_cash_treasury = curr_cash_treasury
        current_day.closing_insta_treasury = curr_insta_treasury
        db.commit()
        st.success("تم إغلاق الوردية بنجاح!")
        st.rerun()
else:
    st.write("---")
    st.warning("⚠️ هذه الوردية مغلقة. إذا أردت تعديل أي طلب أو مصروف، اضغط على الزر التالي لإعادة فتحها:")
    if st.button("🔓 إعادة فتح الوردية للتعديل", type="secondary", use_container_width=True):
        current_day.status = "OPEN"
        db.commit()
        st.success("تم إعادة فتح الوردية بنجاح! يمكنك الآن التعديل وإعادة الإغلاق.")
        st.rerun()

db.close()
