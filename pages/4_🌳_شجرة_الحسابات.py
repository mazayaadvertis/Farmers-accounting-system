"""
🌳 شجرة الحسابات
دليل الحسابات الهرمي: عرض وبحث فوري، وإضافة/تعديل الحسابات.
"""
import streamlit as st
from st_keyup import st_keyup

import auth
import database as db
from ui import page_header

auth.require_login()
page_header("شجرة الحسابات", "🌳")

tab1, tab2 = st.tabs(["📋 عرض وبحث الحسابات", "➕ إضافة / تعديل حساب"])

ACC_TYPES = ["أصول", "خصوم", "حقوق ملكية", "إيرادات", "مصروفات"]

with tab1:
    st.subheader("البحث في الحسابات")
    term = st_keyup("ادخل رقم أو اسم الحساب للبحث المباشر:", key="search_acc")
    st.dataframe(db.search_accounts(term), use_container_width=True, hide_index=True)

with tab2:
    df_all = db.accounts()
    parent_options = ["0 - لا يوجد (حساب رئيسي)"] + db.account_options(df_all)

    mode = st.radio("وضع العمل:", ["إضافة حساب جديد", "تعديل حساب حالي"], horizontal=True)

    selected = None
    if mode == "تعديل حساب حالي":
        acc_to_edit = st.selectbox("اختر الحساب المراد تعديله:", parent_options[1:])
        if acc_to_edit:
            edit_code = int(acc_to_edit.split(" - ")[0])
            mask = df_all["رقم الحساب"].astype(float) == float(edit_code)
            rows = df_all[mask]
            selected = rows.iloc[0] if not rows.empty else None

    with st.form("acc_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            default_code = int(selected["رقم الحساب"]) if selected is not None else 1000
            acc_code = st.number_input("رقم الحساب", step=1, value=default_code,
                                       disabled=(mode == "تعديل حساب حالي"))
            default_name = str(selected["اسم الحساب"]) if selected is not None else ""
            acc_name = st.text_input("اسم الحساب", value=default_name)
            acc_type = st.selectbox("نوع الحساب", ACC_TYPES,
                                    index=0 if selected is None else ACC_TYPES.index(selected["نوع الحساب"]))
            nature = st.selectbox("طبيعة الحساب", ["مدين", "دائن"],
                                  index=0 if selected is None else ["مدين", "دائن"].index(selected["طبيعة الحساب"]))
        with c2:
            p_idx = 0
            if selected is not None:
                p_code = selected["الحساب الأب"]
                for i, opt in enumerate(parent_options):
                    if opt.startswith(f"{int(p_code)} -"):
                        p_idx = i
                        break
            parent = st.selectbox("الحساب الأب", options=parent_options, index=p_idx)
            level = st.number_input("المستوى المحاسبي", min_value=1, max_value=5,
                                    value=int(selected["المستوى"]) if selected is not None else 4)
            is_sub = st.selectbox("حساب حركة (قابل للترحيل)", ["نعم", "لا"],
                                  index=0 if selected is None or selected["حساب حركة (قابل للترحيل)"] == "نعم" else 1)
            currency = st.selectbox("العملة", ["YER", "SAR", "USD"], index=0)
            is_active = st.selectbox("الحالة", ["نشط", "غير نشط"],
                                     index=0 if selected is None or selected["الحالة"] == "نشط" else 1)
        submitted = st.form_submit_button("حفظ البيانات")

    if submitted:
        if not acc_name.strip():
            st.error("يرجى إدخال اسم الحساب")
        else:
            p_code = int(parent.split(" - ")[0])
            try:
                if mode == "إضافة حساب جديد":
                    ok, msg = db.add_account(acc_code, acc_name.strip(), p_code, level,
                                             acc_type, nature, is_sub, currency, is_active)
                else:
                    ok, msg = db.update_account(acc_code, acc_name.strip(), p_code, level,
                                                acc_type, nature, is_sub, currency, is_active)
                st.success(msg) if ok else st.error(msg)
            except RuntimeError as e:
                st.error(str(e))
