import streamlit as st
from database.connection import init_db, get_db
from database.models import Region

# تم تغيير الاسم إلى Catchy Finance
st.set_page_config(page_title="Catchy Finance", page_icon="💰", layout="wide")
init_db()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif !important; direction: rtl; text-align: right; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    div[data-testid="metric-container"] { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

db = next(get_db())

if db.query(Region).count() == 0:
    db.add_all([Region(name="الشروق"), Region(name="مدينتي")])
    db.commit()

if 'current_region_id' not in st.session_state:
    st.title("💼 Catchy Finance")
    st.subheader("اختر المنطقة للبدء:")
    
    regions = db.query(Region).filter(Region.is_active == True).all()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        for r in regions:
            if st.button(f"📍 {r.name}", use_container_width=True):
                st.session_state['current_region_id'] = r.id
                st.session_state['current_region_name'] = r.name
                st.rerun()
else:
    st.sidebar.success(f"🏢 المنطقة الحالية: {st.session_state['current_region_name']}")
    if st.sidebar.button("🔄 تغيير المنطقة", use_container_width=True):
        del st.session_state['current_region_id']
        del st.session_state['current_region_name']
        st.rerun()
        
    st.title(f"🏢 Catchy Finance - {st.session_state['current_region_name']}")
    st.info("👈 اختر Shift من القائمة الجانبية لتسجيل اليومية.")

db.close()