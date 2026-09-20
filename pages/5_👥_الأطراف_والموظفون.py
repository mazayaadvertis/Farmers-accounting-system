"""
👥 الأطراف والموظفون
إدارة المزارعين والمشترين والموظفين: إضافة جديد واستعراض السجلات.
"""
from datetime import datetime

import pandas as pd
import streamlit as st

import auth
import database as db
from ui import page_header

auth.require_login()
page_header("الأطراف والموظفون", "👥")

tab_f, tab_b, tab_e = st.tabs(["🌾 المزارعون", "🛒 المشترون", "🧑‍💼 الموظفون"])

# =================================================================
# المزارعون
# =================================================================
with tab_f:
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("new_farmer", clear_on_submit=True):
            st.subheader("إضافة مزارع")
            f_name = st.text_input("اسم المزارع (الرباعي)")
            f_phone = st.text_input("رقم الهاتف")
            f_whatsapp = st.text_input("رقم الواتساب")
            f_gov = st.text_input("المحافظة")
            f_dist = st.text_input("المديرية")
            f_bal = st.number_input("الرصيد الافتتاحي", min_value=0.0, value=0.0)
            f_office_pct = st.number_input("نسبة عمولة المكتب", min_value=0.0, value=0.05, step=0.01, format="%.4f")
            f_zakat_pct = st.number_input("نسبة الزكاة", min_value=0.0, value=0.04, step=0.01, format="%.4f")
            f_crops = st.text_input("أهم المحاصيل")
            f_notes = st.text_input("ملاحظات")
            if st.form_submit_button("💾 حفظ المزارع"):
                if not f_name.strip():
                    st.error("يرجى إدخال اسم المزارع")
                else:
                    try:
                        db.append_rows(db.SH_FARMERS, pd.DataFrame([{
                            "رقم الحساب": db.next_id(db.SH_FARMERS, "رقم الحساب"),
                            "اسم المزارع": f_name.strip(),
                            "رقم الهاتف الرئيسي": f_phone or None,
                            "رقم هاتف الواتساب": f_whatsapp or None,
                            "المحافظة": f_gov or None,
                            "المديريه": f_dist or None,
                            "الرصيد الافتتاحي": f_bal,
                            "الرصيد الحالي": f_bal,
                            "نسبة عمولة المكتب له": f_office_pct,
                            "نسبة الزكاة": f_zakat_pct,
                            "أهم المحاصيل": f_crops or None,
                            "حالة المزارع": 1,
                            "ملاحظات خاصة بالتعامل.": f_notes or None,
                            "تاريخ الاضافه": datetime.today(),
                        }]))
                        st.success(f"تمت إضافة المزارع {f_name}")
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
    with c2:
        st.subheader("سجل المزارعين")
        df = db.farmers()
        st.dataframe(df, use_container_width=True, hide_index=True)

# =================================================================
# المشترون
# =================================================================
with tab_b:
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("new_buyer", clear_on_submit=True):
            st.subheader("إضافة مشتري")
            b_name = st.text_input("اسم المشتري")
            b_nick = st.text_input("اسم الشهرة")
            b_company = st.text_input("اسم الشركة")
            b_national = st.text_input("رقم البطاقة الشخصية")
            b_phone = st.text_input("رقم الهاتف")
            b_whatsapp = st.text_input("رقم الواتساب")
            b_guarantor = st.text_input("اسم الضمين")
            b_gov = st.text_input("المحافظة")
            b_dist = st.text_input("المديرية")
            b_bal = st.number_input("الرصيد الافتتاحي", min_value=0.0, value=0.0)
            b_fee = st.number_input("رسوم الدلالة", min_value=0.0, value=0.0)
            if st.form_submit_button("💾 حفظ المشتري"):
                if not b_name.strip():
                    st.error("يرجى إدخال اسم المشتري")
                else:
                    try:
                        db.append_rows(db.SH_BUYERS, pd.DataFrame([{
                            "رقم حساب المشتري": db.next_id(db.SH_BUYERS, "رقم حساب المشتري"),
                            "اسم المشتري": b_name.strip(),
                            "اسم الشهرة": b_nick or None,
                            "اسم الشركه": b_company or None,
                            "رقم البطاقه الشخصيه": b_national or None,
                            "رقم الهاتف المشتري الواتساب": b_whatsapp or None,
                            "رقم تلفون المشتري": b_phone or None,
                            "اسم الضمين على المشتري": b_guarantor or None,
                            "المحافظة": b_gov or None,
                            "المديريه": b_dist or None,
                            "الرصيد الافتتاحي": b_bal,
                            "الرصيد الحالي": b_bal,
                            "رسوم الدلاله": b_fee,
                            "تاريخ الاضافه": datetime.today(),
                            "الحالة": 1,
                        }]))
                        st.success(f"تمت إضافة المشتري {b_name}")
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
    with c2:
        st.subheader("سجل المشترين")
        st.dataframe(db.buyers(), use_container_width=True, hide_index=True)

# =================================================================
# الموظفون
# =================================================================
with tab_e:
    roles = db.roles_list()
    role_options = roles + ["➕ دور جديد..."]
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("new_emp", clear_on_submit=True):
            st.subheader("إضافة موظف / صندوق")
            e_code = st.text_input("كود الموظف", value=str(db.next_id(db.SH_EMPLOYEES, "كود الموظف")))
            e_name = st.text_input("اسم الموظف / الصندوق")
            e_role = st.selectbox("الصفة / الوظيفة", options=role_options)
            e_role_new = ""
            if e_role == "➕ دور جديد...":
                e_role_new = st.text_input("اكتب الدور الجديد")
            e_role2 = st.text_input("دور وظيفي ثاني")
            e_adv = st.selectbox("الامتياز", ["موظف", "شريك", "مندوب"])
            e_phone = st.text_input("رقم الهاتف")
            e_bal = st.number_input("الرصيد الحالي", min_value=0.0, value=0.0)
            e_salary = st.number_input("الراتب", min_value=0.0, value=0.0)
            e_pct = st.number_input("النسبة/الحافز", min_value=0.0, value=0.0)
            e_status = st.selectbox("الحالة", ["نشط", "غير نشط"])
            if st.form_submit_button("💾 حفظ الموظف"):
                final_role = e_role_new.strip() if e_role == "➕ دور جديد..." else e_role
                if not e_name.strip():
                    st.error("يرجى إدخال اسم الموظف")
                elif not final_role:
                    st.error("يرجى تحديد الوظيفة")
                else:
                    try:
                        db.append_rows(db.SH_EMPLOYEES, pd.DataFrame([{
                            "كود الموظف": int(e_code),
                            "اسم الموظف": e_name.strip(),
                            "الصفة / الوظيفة": final_role,
                            "دور وظيفي ثاني": e_role2 or None,
                            "الامتياز": e_adv,
                            "رقم الهاتف": e_phone or None,
                            "الرصيد الحالي": e_bal,
                            "الراتب": e_salary,
                            "النسبه/الحافز": e_pct,
                            "تاريخ الاضافه": datetime.today(),
                            "الحالة": 1 if e_status == "نشط" else 0,
                        }]))
                        st.success(f"تمت إضافة {e_name}")
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
    with c2:
        st.subheader("سجل الموظفين")
        st.dataframe(db.employees(), use_container_width=True, hide_index=True)
