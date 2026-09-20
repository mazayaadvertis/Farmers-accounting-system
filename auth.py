"""
المصادقة وإدارة المستخدمين — شاشة دخول أنيقة + تسجيل حساب جديد
كلمات المرور تُخزَّن مشفّرة (PBKDF2-SHA256) في ورقة TableUsers داخل ملف Excel.
"""
import hashlib
import secrets
from datetime import datetime

import pandas as pd
import streamlit as st

import database as db

SESSION_KEY = "auth_user"
ROLE_ADMIN = "مدير النظام"
ROLE_USER = "مستخدم"
PBKDF2_ITER = 120_000

DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PW = "admin123"


# -----------------------------------------------------------------------------
# تشفير كلمات المرور
# -----------------------------------------------------------------------------
def hash_password(pw):
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", str(pw).encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITER)
    return f"pbkdf2_sha256${PBKDF2_ITER}${salt}${dk.hex()}"


def verify_password(pw, stored):
    try:
        _algo, iters, salt, expected = str(stored).split("$")
        dk = hashlib.pbkdf2_hmac("sha256", str(pw).encode("utf-8"), bytes.fromhex(salt), int(iters))
        return secrets.compare_digest(dk.hex(), expected)
    except (ValueError, TypeError):
        return False


# -----------------------------------------------------------------------------
# قراءة المستخدمين
# -----------------------------------------------------------------------------
def users():
    return db.users()


def find_user(username):
    uname = str(username).strip().lower()
    if not uname:
        return None
    df = users()
    if df.empty or db.UC_USERNAME not in df.columns:
        return None
    mask = df[db.UC_USERNAME].astype(str).str.strip().str.lower() == uname
    return df[mask].iloc[0] if mask.any() else None


def authenticate(username, password):
    """يعيد (صف المستخدم, رسالة خطأ) — أحدهما None."""
    u = find_user(username)
    if u is None:
        return None, "اسم المستخدم غير موجود"
    if str(u[db.UC_STATUS]).strip() != "نشط":
        return None, "الحساب معطّل — راجع مدير النظام"
    if not verify_password(password, u[db.UC_PASSWORD]):
        return None, "كلمة المرور غير صحيحة"
    return u, None


# -----------------------------------------------------------------------------
# إنشاء / تعديل الحسابات
# -----------------------------------------------------------------------------
def _user_row(full_name, username, email, phone, password, role):
    return pd.DataFrame([{
        db.UC_ID: db.next_id(db.SH_USERS, db.UC_ID),
        db.UC_USERNAME: username,
        db.UC_FULLNAME: full_name,
        db.UC_PASSWORD: hash_password(password),
        db.UC_EMAIL: email,
        db.UC_PHONE: phone,
        db.UC_ROLE: role,
        db.UC_STATUS: "نشط",
        db.UC_CREATED: datetime.now().strftime("%Y-%m-%d %H:%M"),
        db.UC_LASTLOGIN: "",
    }])


def register(full_name, username, email, phone, password, confirm):
    """تسجيل حساب جديد — يعيد (صف المستخدم, رسالة خطأ)."""
    full_name, username = str(full_name).strip(), str(username).strip()
    email, phone = str(email).strip(), str(phone).strip()
    if len(full_name) < 3:
        return None, "الرجاء إدخال الاسم الكامل (3 أحرف على الأقل)"
    if len(username) < 3 or " " in username:
        return None, "اسم المستخدم يجب أن يكون 3 أحرف على الأقل وبدون مسافات"
    if find_user(username) is not None:
        return None, "اسم المستخدم مسجّل مسبقاً، اختر اسماً آخر"
    if len(str(password)) < 6:
        return None, "كلمة المرور يجب أن تكون 6 أحرف على الأقل"
    if password != confirm:
        return None, "كلمتا المرور غير متطابقتين"
    if email and "@" not in email:
        return None, "صيغة البريد الإلكتروني غير صحيحة"
    db.append_rows(db.SH_USERS, _user_row(full_name, username, email, phone, password, ROLE_USER))
    return find_user(username), None


def change_password(old, new, confirm):
    u = current_user()
    if not u:
        return False, "انتهت الجلسة، أعد تسجيل الدخول"
    df = users()
    mask = pd.to_numeric(df[db.UC_ID], errors="coerce") == float(u["id"])
    if not mask.any():
        return False, "المستخدم غير موجود"
    if not verify_password(old, df[mask].iloc[0][db.UC_PASSWORD]):
        return False, "كلمة المرور الحالية غير صحيحة"
    if len(str(new)) < 6:
        return False, "كلمة المرور الجديدة قصيرة (6 أحرف على الأقل)"
    if new != confirm:
        return False, "كلمتا المرور الجديدتان غير متطابقتين"
    db.update_user(u["id"], **{db.UC_PASSWORD: hash_password(new)})
    return True, "تم تغيير كلمة المرور بنجاح"


def _touch_last_login(user_id):
    try:
        db.update_user(user_id, **{db.UC_LASTLOGIN: datetime.now().strftime("%Y-%m-%d %H:%M")})
    except Exception:
        pass


def bootstrap():
    """يهيّئ ورقة المستخدمين وينشئ حساب المدير الافتراضي عند أول تشغيل."""
    db.ensure_users_sheet()
    if users().empty:
        db.append_rows(db.SH_USERS, _user_row(
            "مدير النظام", DEFAULT_ADMIN_USER, "", "", DEFAULT_ADMIN_PW, ROLE_ADMIN))
        return DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PW
    return None


# -----------------------------------------------------------------------------
# الجلسة
# -----------------------------------------------------------------------------
def current_user():
    return st.session_state.get(SESSION_KEY)


def is_logged_in():
    return current_user() is not None


def _start_session(row):
    st.session_state[SESSION_KEY] = {
        "id": int(float(row[db.UC_ID])),
        "username": str(row[db.UC_USERNAME]),
        "name": str(row[db.UC_FULLNAME]),
        "role": str(row[db.UC_ROLE]),
    }


def logout():
    st.session_state.pop(SESSION_KEY, None)


def require_login():
    """حارس الصفحات: يعرض شاشة الدخول ويتوقف إن لم يكن المستخدم مسجلاً."""
    if is_logged_in():
        return
    render_auth_page()
    st.stop()


# -----------------------------------------------------------------------------
# واجهة الدخول والتسجيل
# -----------------------------------------------------------------------------
_AUTH_CSS = """
<style>
.stApp { background: linear-gradient(135deg, #06281d 0%, #0d4a33 45%, #1a7a52 100%); }
.stApp:has(.auth-hero) [data-testid="stSidebar"],
.stApp:has(.auth-hero) [data-testid="stHeader"],
.stApp:has(.auth-hero) [data-testid="stToolbar"] { display: none !important; }
.auth-hero { text-align: center; color: #f2fbf6; direction: rtl; margin: 1.4rem 0 1.6rem 0; }
.auth-hero .logo { font-size: 66px; line-height: 1.1; }
.auth-hero h1 { color: #ffffff !important; font-size: 30px !important; margin: .35rem 0 .25rem 0; }
.auth-hero p { color: #bfe8d4 !important; font-size: 16px !important; margin: 0; }
.stApp:has(.auth-hero) [data-testid="stForm"] {
    background: #ffffff; border: 1px solid #e2efe8; border-radius: 20px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, .38); padding: 1.5rem 1.7rem;
    direction: rtl;
}
.stApp:has(.auth-hero) [data-baseweb="tab-list"] { justify-content: center; gap: .4rem; }
.stApp:has(.auth-hero) [data-baseweb="tab-list"] button { color: #d9f2e6 !important; font-weight: 800 !important; }
.stApp:has(.auth-hero) [data-baseweb="tab-list"] button[aria-selected="true"] { color: #ffffff !important; }
.stApp:has(.auth-hero) [data-baseweb="tab-highlight"],
.stApp:has(.auth-hero) [data-baseweb="tab-border"] { background-color: #7fd8b0 !important; }
.stApp:has(.auth-hero) [data-testid="stFormSubmitButton"] button {
    background: linear-gradient(135deg, #0d4a33, #1a8a5c) !important;
    color: #ffffff !important; border: none !important; border-radius: 12px !important;
}
.stApp:has(.auth-hero) [data-testid="stFormSubmitButton"] button:hover {
    background: linear-gradient(135deg, #0b3f2b, #167a51) !important; color: #ffffff !important;
}
.auth-foot { text-align: center; color: #9fd4bb; margin-top: 1.1rem; font-size: 14px; direction: rtl; }
</style>
"""

_HERO = (
    '<div class="auth-hero">'
    '<div class="logo">🌾</div>'
    "<h1>النظام المحاسبي الزراعي</h1>"
    "<p>سجّل الدخول للمتابعة إلى لوحة التحكم</p>"
    "</div>"
)


def render_auth_page():
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    try:
        created = bootstrap()
    except Exception as e:
        st.error(f"تعذر تجهيز جدول المستخدمين: {e}")
        st.stop()

    st.markdown(_HERO, unsafe_allow_html=True)
    if created:
        st.info(f"أول تشغيل: أُنشئ حساب المدير الافتراضي — اسم المستخدم: {created[0]} / "
                f"كلمة المرور: {created[1]} (غيّرها بعد الدخول من قائمة المستخدم)")

    c1, c2, c3 = st.columns([1, 1.15, 1])
    with c2:
        tab_login, tab_register = st.tabs(["🔐 تسجيل الدخول", "📝 حساب جديد"])

        with tab_login:
            with st.form("login_form"):
                u = st.text_input("اسم المستخدم", placeholder="username")
                p = st.text_input("كلمة المرور", type="password")
                if st.form_submit_button("دخول ➜", use_container_width=True, type="primary"):
                    row, err = authenticate(u, p)
                    if row is None:
                        st.error(err)
                    else:
                        _touch_last_login(row[db.UC_ID])
                        _start_session(row)
                        st.rerun()

        with tab_register:
            with st.form("register_form", clear_on_submit=True):
                full = st.text_input("الاسم الكامل")
                un = st.text_input("اسم المستخدم", placeholder="بدون مسافات")
                em = st.text_input("البريد الإلكتروني (اختياري)")
                ph = st.text_input("رقم الهاتف (اختياري)")
                pw = st.text_input("كلمة المرور", type="password")
                pw2 = st.text_input("تأكيد كلمة المرور", type="password")
                if st.form_submit_button("إنشاء الحساب ✨", use_container_width=True, type="primary"):
                    row, err = register(full, un, em, ph, pw, pw2)
                    if row is None:
                        st.error(err)
                    else:
                        _touch_last_login(row[db.UC_ID])
                        _start_session(row)
                        st.rerun()

    st.markdown('<div class="auth-foot">💾 جميع البيانات محفوظة في ملف Excel مع نسخ احتياطي تلقائي</div>',
                unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# صندوق المستخدم في الشريط الجانبي
# -----------------------------------------------------------------------------
def sidebar_user_box():
    u = current_user()
    if not u:
        return
    with st.sidebar:
        st.markdown("---")
        with st.popover(f"👤 {u['name']}", use_container_width=True):
            st.caption(f"اسم المستخدم: {u['username']} — الصلاحية: {u['role']}")
            with st.form("change_pw_form", clear_on_submit=True):
                old = st.text_input("كلمة المرور الحالية", type="password")
                new = st.text_input("كلمة المرور الجديدة", type="password")
                cnf = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
                if st.form_submit_button("💾 حفظ كلمة المرور", use_container_width=True):
                    ok, msg = change_password(old, new, cnf)
                    (st.success if ok else st.error)(msg)
            st.button("🚪 تسجيل الخروج", use_container_width=True, on_click=logout)
