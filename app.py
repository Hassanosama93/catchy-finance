import streamlit as st
from database.connection import init_db, get_db
from database.models import Region

st.set_page_config(page_title="Catchy Finance", page_icon="💧", layout="wide")
init_db()

# كود CSS آمن ومضبوط للموبايل يمنع تداخل القوائم
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    
    /* تطبيق الخط العربي */
    * {
        font-family: 'Tajawal', sans-serif !important;
    }
    
    /* ضبط اتجاه النصوص والقوائم بدون كسر هيكل الموبايل */
    .stMarkdown, .stText, p, h1, h2, h3, h4, label, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* ضبط مسافات الصفحة على الموبايل لتملأ الشاشة بنظافة */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* تجميل الأزرار لتكون مريحة للمس */
    .stButton>button {
        border-radius: 10px;
        min-height: 48px;
        font-size: 16px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

db = next(get_db())

if db.query(Region).count() == 0:
    db.add_all([Region(name="الشروق"), Region(name="مدينتي")])
    db.commit()

# شاشة اختيار المنطقة
if 'current_region_id' not in st.session_state:
    st.markdown("<h2 style='text-align: center;'>💼 Catchy Finance</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>اختر الفرع للبدء:</p>", unsafe_allow_html=True)
    
    regions = db.query(Region).filter(Region.is_active == True).all()
    for r in regions:
        if st.button(f"📍 فرع {r.name}", use_container_width=True):
            st.session_state['current_region_id'] = r.id
            st.session_state['current_region_name'] = r.name
            st.rerun()
else:
    # الشريط الجانبي
    st.sidebar.markdown(f"### 📍 فرع {st.session_state['current_region_name']}")
    if st.sidebar.button("🔄 تغيير الفرع", use_container_width=True):
        del st.session_state['current_region_id']
        del st.session_state['current_region_name']
        st.rerun()
        
    # الشاشة الرئيسية واضحة ونظيفة
    st.markdown("<h2 style='text-align: center;'>Catchy Finance</h2>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center; color: #2e7bcf;'>فرع {st.session_state['current_region_name']}</h4>", unsafe_allow_html=True)
    st.divider()
    
    st.info("👈 اضغط على السهم في أعلى اليسار (>) واختر **Shift** للبدء.")

db.close()
