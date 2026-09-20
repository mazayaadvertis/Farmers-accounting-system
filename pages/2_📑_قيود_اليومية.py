"""
📑 قيود اليومية
استعراض القيود وتسجيل قيد يدوي جديد مع التحقق من التوازن المدين/الدائن
وربط الحسابات الرئيسية بالأطراف (مزارع/مشتري/موظف).
"""
from datetime import datetime

import pandas as pd
import streamlit as st

import auth
import database as db
from ui import page_header

auth.require_login()
page_header("قيود اليومية", "📑")

entities = db.entity_lists()
buyers_opts = [f"{c} - {n}" for c, n, _ in entities["buyers"]]
farmers_opts = [f"{c} - {n}" for c, n, _ in entities["farmers"]]
employees_opts = [f"{c} - {n}" for c, n, _ in entities["employees"]]

df_all_accounts = db.accounts()
main_opts = db.account_options()

GENERAL = "0 - لا يوجد (حساب عام)"

tab_view, tab_entry = st.tabs(["📊 استعراض القيود", "✍️ تسجيل قيد جديد"])

# =================================================================
# تبويب 1: الاستعراض
# =================================================================
with tab_view:
    j = db.journal()
    if j.empty:
        st.info("لا توجد قيود مسجلة")
    else:
        ids = sorted(pd.to_numeric(j["رقم القيد"], errors="coerce").dropna().unique(), reverse=True)
        c1, c2 = st.columns(2)
        sel_id = c1.selectbox("استعراض قيد برقمه", options=["—"] + [int(i) for i in ids])
        types = ["—"] + sorted(j["نوع الحركة"].astype(str).unique().tolist())
        sel_type = c2.selectbox("تصفية بنوع الحركة", options=types)

        view = j.copy()
        if sel_type != "—":
            view = view[view["نوع الحركة"].astype(str) == sel_type]
        if sel_id != "—":
            view = view[pd.to_numeric(view["رقم القيد"], errors="coerce") == float(sel_id)]

        show = view[["رقم القيد", "تاريخ القيد", "نوع الحركة", "رقم المرجع",
                     "رقم الحساب الرئيسي", "اسم الحساب", "رقم الحساب الفرعي",
                     "اسم صاحب الحساب", "المبلغ المدين", "المبلغ الدائن",
                     "البيان / شرح القيد التلقائي"]]
        st.dataframe(show, use_container_width=True, hide_index=True)

        if sel_id != "—":
            dr = pd.to_numeric(view["المبلغ المدين"], errors="coerce").fillna(0).sum()
            cr = pd.to_numeric(view["المبلغ الدائن"], errors="coerce").fillna(0).sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("إجمالي مدين القيد", f"{dr:,.2f}")
            c2.metric("إجمالي دائن القيد", f"{cr:,.2f}")
            c3.metric("الحالة", "متوازن ✅" if abs(dr - cr) < 0.01 else f"غير متوازن ({dr - cr:,.2f}) ❌")

# =================================================================
# تبويب 2: إدخال قيد
# =================================================================
with tab_entry:
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        entry_id = st.number_input("رقم القيد", step=1,
                                   value=db.next_id(db.SH_JOURNAL, "رقم القيد"))
    with c2:
        entry_date = st.date_input("تاريخ القيد", datetime.now())
    with c3:
        entry_time = st.time_input("وقت القيد", datetime.now())
    with c4:
        trans_type = st.selectbox("نوع الحركة",
                                  ["قيد يدوي", "فاتورة مزارع", "سند قبض", "سند صرف", "تسوية"])
    with c5:
        ref_no = st.text_input("رقم المرجع / الورقة", value="يدوي")

    st.markdown("---")
    st.subheader("أطراف القيد (المدين والدائن)")

    if "journal_rows" not in st.session_state:
        st.session_state.journal_rows = [
            {"debit": 0.0, "credit": 0.0, "desc": ""},
            {"debit": 0.0, "credit": 0.0, "desc": ""},
        ]

    def add_row():
        st.session_state.journal_rows.append({"debit": 0.0, "credit": 0.0, "desc": ""})

    def remove_row(i):
        if len(st.session_state.journal_rows) > 2:
            st.session_state.journal_rows.pop(i)

    rows_to_save = []

    for i in range(len(st.session_state.journal_rows)):
        st.markdown(f"**الطرف رقم ({i + 1})**")
        c1, c2, c3, c4, c5, c6 = st.columns([1.3, 1.3, 2.6, 2.6, 2.2, 0.5])
        saved = st.session_state.journal_rows[i]

        with c1:
            debit = st.number_input(f"مدين #{i+1}", min_value=0.0, step=100.0,
                                    value=float(saved["debit"]), key=f"deb_{i}")
        with c2:
            credit = st.number_input(f"دائن #{i+1}", min_value=0.0, step=100.0,
                                     value=float(saved["credit"]), key=f"cred_{i}")
        with c3:
            main_sel = st.selectbox(f"الحساب الرئيسي #{i+1}", main_opts, key=f"main_{i}")
            main_code = int(main_sel.split(" - ")[0])
            main_name = main_sel.split(" - ", 1)[1]

            acc_row = df_all_accounts[pd.to_numeric(df_all_accounts["رقم الحساب"], errors="coerce") == main_code]
            parent = int(acc_row.iloc[0]["الحساب الأب"]) if not acc_row.empty else 0
            s_code, s_parent = str(main_code), str(parent)

            if s_code.startswith("112") or s_parent.startswith("112") or "مشتر" in main_name:
                sub_opts = [GENERAL] + buyers_opts
            elif s_code.startswith("211") or s_parent.startswith("211") or "مزارع" in main_name:
                sub_opts = [GENERAL] + farmers_opts
            elif (s_code.startswith("511") or s_parent.startswith("511")
                  or s_code.startswith("1132") or s_parent.startswith("1132")
                  or "موظف" in main_name):
                sub_opts = [GENERAL] + employees_opts
            else:
                sub_opts = [GENERAL]
        with c4:
            sub_sel = st.selectbox(f"صاحب الحساب/الكيان #{i+1}", sub_opts, key=f"sub_{i}")
        with c5:
            desc = st.text_input(f"البيان #{i+1}", value=saved["desc"], key=f"desc_{i}")
        with c6:
            if st.button("❌", key=f"del_{i}"):
                remove_row(i)
                st.rerun()

        if sub_sel == GENERAL:
            sub_code, sub_name = 0, ""
        else:
            sub_code = int(sub_sel.split(" - ")[0])
            sub_name = sub_sel.split(" - ", 1)[1]

        st.session_state.journal_rows[i].update({"debit": debit, "credit": credit, "desc": desc})
        rows_to_save.append({
            "main_code": main_code, "main_name": main_name,
            "sub_code": sub_code, "sub_name": sub_name,
            "debit": debit, "credit": credit, "desc": desc,
        })

    st.button("➕ إضافة طرف جديد للقيد", on_click=add_row)

    tot_dr = sum(r["debit"] for r in rows_to_save)
    tot_cr = sum(r["credit"] for r in rows_to_save)
    diff = tot_dr - tot_cr

    st.markdown("---")
    c_t1, c_t2, c_t3 = st.columns(3)
    c_t1.metric("إجمالي المدين", f"{tot_dr:,.2f}")
    c_t2.metric("إجمالي الدائن", f"{tot_cr:,.2f}")
    c_t3.metric("الفارق", f"{diff:,.2f}", delta_color="inverse")

    if st.button("💾 حفظ وتوجيه القيد", type="primary"):
        if tot_dr == 0 and tot_cr == 0:
            st.error("❌ لا يمكن حفظ قيد بمبالغ صفرية")
        elif round(tot_dr, 2) != round(tot_cr, 2):
            st.error(f"❌ القيد غير متوازن: مدين ({tot_dr:,.2f}) ≠ دائن ({tot_cr:,.2f})")
        else:
            try:
                ok, msg = db.save_journal_entry(
                    entry_id=entry_id,
                    entry_date=f"{entry_date} {entry_time}",
                    trans_type=trans_type,
                    ref_no=ref_no,
                    rows_data=rows_to_save,
                )
                if ok:
                    st.success(f"✅ {msg}")
                    st.session_state.journal_rows = [
                        {"debit": 0.0, "credit": 0.0, "desc": ""},
                        {"debit": 0.0, "credit": 0.0, "desc": ""},
                    ]
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            except RuntimeError as e:
                st.error(str(e))
