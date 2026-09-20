"""
💰 سندات القبض والصرف
تسجيل حركات النقدية الواردة والصادرة في ورقة TablePayments
مع خيار توليد القيد المحاسبي التلقائي (سند قبض / سند صرف).
"""
from datetime import datetime

import pandas as pd
import streamlit as st

import auth
import database as db
from ui import page_header

auth.require_login()
page_header("سندات القبض والصرف", "💰")

# خريطة أولويات الكيانات لحساباتها الرئيسية
PREFIX_MAIN = {"112": 1121, "211": 2111, "511": 11322, "113": 11322}

entities = db.entity_lists()
buyers_opts = [f"{c} - {n}" for c, n, _ in entities["buyers"]]
farmers_opts = [f"{c} - {n}" for c, n, _ in entities["farmers"]]
employees_opts = [f"{c} - {n}" for c, n, _ in entities["employees"]]
entity_kind_opts = ["مشتري", "مزارع", "موظف", "يدوي (حساب آخر)"]
kind_lists = {"مشتري": buyers_opts, "مزارع": farmers_opts, "موظف": employees_opts}

cash_opts = db.account_options(db.cash_accounts())
if not cash_opts:
    cash_opts = db.account_options(db.sub_accounts())

tab_reg, tab_new = st.tabs(["📋 سجل السندات", "📝 سند جديد"])

# =================================================================
# تبويب 1: السجل
# =================================================================
with tab_reg:
    p = db.payments()
    if p.empty:
        st.info("لا توجد سندات مسجلة بعد")
    else:
        st.dataframe(p, use_container_width=True, hide_index=True)

# =================================================================
# تبويب 2: سند جديد
# =================================================================
with tab_new:
    c1, c2, c3 = st.columns(3)
    with c1:
        pay_type = st.selectbox("نوع السند", ["سند قبض", "سند صرف"])
        pay_date = st.date_input("تاريخ الحركة", datetime.today())
    with c2:
        amount = st.number_input("المبلغ", min_value=0.0, step=1000.0)
        method = st.selectbox("طريقة الدفع", ["نقداً", "حوالة مصرفية", "شبكة صرافة"])
    with c3:
        network = st.text_input("اسم شبكة الصرافة / البنك")
        transfer_no = st.text_input("رقم الحوالة / العملية")

    st.markdown("---")
    st.subheader("الأطراف")

    c1, c2 = st.columns(2)
    with c1:
        cash_sel = st.selectbox("الصندوق / الخزينة (حسابنا النقدي)", cash_opts)
        cash_code = int(cash_sel.split(" - ")[0])
        cash_name = cash_sel.split(" - ", 1)[1]
    with c2:
        kind = st.selectbox("نوع الطرف الآخر", entity_kind_opts)
        if kind == "يدوي (حساب آخر)":
            manual_opts = db.account_options()
            man_sel = st.selectbox("الحساب الرئيسي للطرف", manual_opts)
            man_code = int(man_sel.split(" - ")[0])
            man_name = st.text_input("اسم الطرف", value=man_sel.split(" - ", 1)[1])
            party_code, party_name = man_code, man_name
            party_main_code, party_main_name = man_code, man_sel.split(" - ", 1)[1]
        else:
            opts = kind_lists[kind] if kind_lists[kind] else ["(لا يوجد — أضف من صفحة الأطراف)"]
            sel = st.selectbox("الطرف", opts)
            if sel.startswith("("):
                party_code, party_name = 0, ""
                party_main_code, party_main_name = 0, ""
            else:
                party_code = int(sel.split(" - ")[0])
                party_name = sel.split(" - ", 1)[1]
                prefix = str(party_code)[:3]
                main_c = PREFIX_MAIN.get(prefix)
                if main_c:
                    r = db.find_account(main_c)
                    party_main_code = main_c
                    party_main_name = str(r["اسم الحساب"]) if r is not None else ""
                else:
                    party_main_code, party_main_name = 0, ""

    notes = st.text_area("ملاحظات والبيان")

    if pay_type == "سند قبض":
        st.info(f"💵 قبض: يدخل مبلغ **{amount:,.2f}** إلى {cash_name} من {party_name or 'الطرف'}")
        payer_code, payer_name = party_code, party_name
        recv_code, recv_name = cash_code, cash_name
    else:
        st.info(f"💸 صرف: يخرج مبلغ **{amount:,.2f}** من {cash_name} إلى {party_name or 'الطرف'}")
        payer_code, payer_name = cash_code, cash_name
        recv_code, recv_name = party_code, party_name

    make_journal = st.checkbox("✅ توليد القيد المحاسبي التلقائي للسند", value=True)

    if st.button("💾 حفظ السند", type="primary", use_container_width=True):
        if amount <= 0:
            st.error("يرجى إدخال مبلغ صحيح")
        elif party_code == 0:
            st.error("يرجى اختيار الطرف الآخر للسند")
        else:
            try:
                pay_id = db.next_id(db.SH_PAYMENTS, "رقم السند")
                db.append_payment({
                    "رقم السند": pay_id,
                    "نوع السند": pay_type,
                    "رقم حساب الدافع": payer_code,
                    "اسم الدافع": payer_name,
                    "رقم حساب المستلم": recv_code,
                    "اسم المستلم": recv_name,
                    "المبلغ المدفوع": amount,
                    "تاريخ الحركة": datetime.combine(pay_date, datetime.now().time()),
                    "طريقه الدفع": method,
                    "اسم شبكة الصرافة": network or None,
                    "رقم الحواله": transfer_no or None,
                    "ملاحظات والبيان": notes or None,
                })

                if make_journal:
                    if pay_type == "سند قبض":
                        rows = [
                            {"main_code": cash_code, "main_name": cash_name, "sub_code": 0, "sub_name": "",
                             "debit": round(amount, 2), "credit": 0.0,
                             "desc": f"{pay_type} رقم {pay_id} — تحصيل نقدي"},
                            {"main_code": party_main_code, "main_name": party_main_name,
                             "sub_code": party_code, "sub_name": party_name,
                             "debit": 0.0, "credit": round(amount, 2),
                             "desc": f"{pay_type} رقم {pay_id} — من {party_name}"},
                        ]
                    else:
                        rows = [
                            {"main_code": party_main_code, "main_name": party_main_name,
                             "sub_code": party_code, "sub_name": party_name,
                             "debit": round(amount, 2), "credit": 0.0,
                             "desc": f"{pay_type} رقم {pay_id} — إلى {party_name}"},
                            {"main_code": cash_code, "main_name": cash_name, "sub_code": 0, "sub_name": "",
                             "debit": 0.0, "credit": round(amount, 2),
                             "desc": f"{pay_type} رقم {pay_id} — صرف نقدي"},
                        ]
                    entry_id = db.next_id(db.SH_JOURNAL, "رقم القيد")
                    ok, jmsg = db.save_journal_entry(entry_id, pay_date, pay_type, f"سند رقم {pay_id}", rows)
                    if ok:
                        st.success(f"تم حفظ السند رقم {pay_id} وتوليد القيد المحاسبي رقم {entry_id}")
                    else:
                        st.warning(f"تم حفظ السند رقم {pay_id}، لكن توليد القيد فشل: {jmsg}")
                else:
                    st.success(f"تم حفظ السند رقم {pay_id}")
                st.rerun()
            except RuntimeError as e:
                st.error(str(e))
