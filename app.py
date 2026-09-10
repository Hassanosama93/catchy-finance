import streamlit as st
from database.connection import init_db, get_db
from database.models import Region

st.set_page_config(page_title="Catchy Finance", page_icon="💼", layout="wide", initial_sidebar_state="collapsed")
init_db()

# كود CSS ثوري للموبايل: يحذف القوائم المشوهة ويجعل الكروت مضغوطة وأنيقة
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');
    
    * { font-family: 'Tajawal', sans-serif !important; }
    
    /* ضبط اتجاه النصوص */
    .stMarkdown, p, h1, h2, h3, h4, label { direction: rtl !important; text-align: right !important; }
    
    /* إخفاء القوائم الجانبية المزعجة والأسهم المشوهة */
    [data-testid="collapsedControl"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    header { visibility: hidden; }
    
    /* هوامش الموبايل */
    .block-container {
        padding: 1rem 0.8rem 3rem 0.8rem !important;
        max-width: 100% !important;
    }
    
    /* كروت الأرقام المضغوطة الأنيقة */
    div[data-testid="metric-container"] {
        background: #181c24;
        border: 1px solid #2d3748;
        padding: 10px 14px !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    div[data-testid="stMetricValue"] {
        font-size: 22px !important;
        font-weight: 800 !important;
        color: #00d2ff !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        color: #a0aec0 !important;
    }
    
    /* أزرار لمس مريحة */
    .stButton>button {
        border-radius: 10px !important;
        min-height: 46px !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

db = next(get_db())

if db.query(Region).count() == 0:
    db.add_all([Region(name="الشروق"), Region(name="مدينتي")])
    db.commit()

# اختيار الفرع
if 'current_region_id' not in st.session_state:
    st.markdown("<h2 style='text-align: center; color: #00d2ff; margin-top: 30px;'>💼 Catchy Finance</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a0aec0;'>اختر الفرع للبدء:</p>", unsafe_allow_html=True)
    
    regions = db.query(Region).filter(Region.is_active == True).all()
    for r in regions:
        if st.button(f"📍 فرع {r.name}", use_container_width=True):
            st.session_state['current_region_id'] = r.id
            st.session_state['current_region_name'] = r.name
            st.rerun()
else:
    # شريط تنقل علوي سريع ومريح للموبايل
    c_top1, c_top2 = st.columns([3, 1])
    c_top1.markdown(f"<h3 style='margin:0; color:#00d2ff;'>فرع {st.session_state['current_region_name']}</h3>", unsafe_allow_html=True)
    if c_top2.button("🔄 الفرع", use_container_width=True):
        del st.session_state['current_region_id']
        del st.session_state['current_region_name']
        st.rerun()
        
    st.markdown("---")
    st.info("💡 استخدم القائمة السريعة بالأسفل أو تنقل مباشرة:")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("🚗 الوردية اليومية (Shift)", use_container_width=True, type="primary"):
            st.switch_page("pages/1_shift.py")
        if st.button("📊 التقارير والرواتب", use_container_width=True):
            st.switch_page("pages/3_reports.py")
    with col_nav2:
        if st.button("🏖️ سجل الإجازات", use_container_width=True):
            st.switch_page("pages/4_leaves.py")
        if st.button("⚙️ إعدادات النظام", use_container_width=True):
            st.switch_page("pages/2_settings.py")

db.close()
