"""واجهات مشتركة وتنسيقات مخصصة بين صفحات التطبيق."""
import streamlit as st
import auth

# تصميم CSS شامل لمنح التطبيق مظهر احترافي ونقل القائمة لليمين
CSS = """
    <style>
    /* 1. استيراد خط عربي حديث (Tajawal) */
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');

    /* 2. التعديل الأهم: قلب اتجاه التطبيق بالكامل لينقل القائمة الجانبية لليمين */
    .stApp {
        direction: rtl;
    }

    /* 3. ضبط الخط العام واتجاه الصفحة والتطبيق */
    html, body, [class*="css"], div, span, p, label, input, button, select, textarea {
        font-size: 15px !important;
        font-weight: 500 !important;
    }
    
    .stTextInput input, .stNumberInput input, .stSelectbox, .stDateInput input,
    .stTimeInput input, .stTextArea textarea, .stMultiselect {
        font-family: 'Tajawal', sans-serif !important;
        font-size: 15px !important;
        font-weight: 500 !important;
    }

    /* 4. تنسيق القائمة الجانبية والحدود الفاصلة */
    [data-testid="stSidebar"] { 
        background-color: #f8fafc !important;
        /* وضع خط فاصل على يسار القائمة لأنها أصبحت في اليمين */
        border-left: 1px solid #e2e8f0 !important; 
        border-right: none !important;
    }

    /* 5. إخفاء عناصر Streamlit الافتراضية للظهور بمظهر مخصص */
    #MainMenu {visibility: visible;}
    footer {visibility: visible;}
    header {visibility: visible;}
    [data-testid="stDecoration"] {display: none;}

    /* 6. استغلال أقصى مساحة ممكّنة وتقليل الهوامش الخارجية */
    .main .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 0.8rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 99% !important;
    }

    /* 7. تقليل المسافة الرأسية بين عناصر الصفحة */
    div[data-testid="stVerticalBlock"] {
        gap: 0.35rem !important;
    }

    /* 8. ضغط ارتفاع الحقول والمدخلات لجعل الواجهة مدمجة وعملية */
    div[data-baseweb="input"] > div, 
    div[data-baseweb="select"] > div {
        min-height: 34px !important;
        border-radius: 6px !important;
    }

    .stTextInput input, .stNumberInput input, .stSelectbox input, .stDateInput input {
        padding-top: 2px !important;
        padding-bottom: 2px !important;
    }

    /* 9. تحسين مظهر عناوين الصفحات والجداول */
    h1 {
        padding-top: 0rem !important;
        padding-bottom: 0.3rem !important;
        margin-bottom: 0.4rem !important;
        font-size: 1.65rem !important;
        color: #1e293b !important;
        font-weight: 700 !important;
        border-bottom: 2px solid #e2e8f0;
    }

    h2, h3, h4 {
        font-weight: 700 !important;
        color: #334155 !important;
        margin-top: 0.3rem !important;
        margin-bottom: 0.3rem !important;
    }

    /* 10. تحسين تصميم الأزرار */
    .stButton > button {
        border-radius: 6px !important;
        font-weight: 700 !important;
        border: 1px solid #2563eb !important;
        background-color: #2563eb !important;
        color: #ffffff !important;
        padding: 0.3rem 0.8rem !important;
        transition: all 0.2s ease-in-out;
    }

    .stButton > button:hover {
        background-color: #1d4ed8 !important;
        border-color: #1d4ed8 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* 11. بطاقات إحصائية ومكونات مخصصة */
    .flask-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 8px;
    }

    .metric-title {
        font-size: 13px;
        color: #64748b;
        font-weight: 600;
    }

    .metric-value {
        font-size: 22px;
        color: #0f172a;
        font-weight: 700;
    }
    </style>
"""


def inject_css():
    """حقن ملف الـ CSS المخصص في الصفحة."""
    st.markdown(CSS, unsafe_allow_html=True)


def page_setup(title, icon="🌾"):
    """للملف الرئيسي فقط (يستدعي set_page_config بخصائص متقدمة)."""
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",  
    )
    inject_css()
    st.title(f"{icon} {title}")


def page_header(title, icon="🌾"):
    """للصفحات الفرعية في مجلد pages (ممنوع فيها set_page_config)."""
    inject_css()
    auth.sidebar_user_box()
    st.title(f"{icon} {title}")


def render_metric_card(title: str, value: str, subtext: str = ""):
    """دالة اختياريّة لعرض بطاقة إحصائية مخصصة."""
    subtext_html = f"<div style='font-size:12px; color:#16a34a; margin-top:2px;'>{subtext}</div>" if subtext else ""
    card_html = f"""
        <div class="flask-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            {subtext_html}
        </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
st.write('<div data-testid="stSidebarCollapseButton" class="st-emotion-cache-qmp9ai eelgd2m10"><button kind="headerNoPadding" data-testid="stBaseButton-headerNoPadding" aria-label="" class="st-emotion-cache-1aplgmp el831t615"><span color="rgba(49, 51, 63, 0.6)" class="st-emotion-cache-2x5h05 ewh6kot2"><span color="rgba(49, 51, 63, 0.6)" data-testid="stIconMaterial" translate="no" class="st-emotion-cache-5r6ut5 ed4y4ls0">keyboard_double_arrow_left</span></span></button></div>')