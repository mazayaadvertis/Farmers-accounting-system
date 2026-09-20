"""
📊 التقارير المالية
ميزان المراجعة، كشف حساب تفصيلي لأي طرف، وملخص الفواتير.
"""
import pandas as pd
import streamlit as st

import auth
import database as db
from ui import page_header

auth.require_login()
page_header("التقارير المالية", "📊")

tab_tb, tab_led, tab_inv = st.tabs(["⚖️ ميزان المراجعة", "📒 كشف حساب", "🧾 ملخص الفواتير"])

# =================================================================
# ميزان المراجعة
# =================================================================
with tab_tb:
    tb = db.trial_balance()
    if tb.empty:
        st.info("لا توجد قيود لعرض ميزان المراجعة")
    else:
        dr_total = tb["إجمالي مدين"].sum()
        cr_total = tb["إجمالي دائن"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي المدين", f"{dr_total:,.2f}")
        c2.metric("إجمالي الدائن", f"{cr_total:,.2f}")
        c3.metric("الحالة", "متوازن ✅" if abs(dr_total - cr_total) < 0.01 else "غير متوازن ❌")
        st.dataframe(tb, use_container_width=True, hide_index=True)

# =================================================================
# كشف حساب
# =================================================================
with tab_led:
    j = db.journal()
    if j.empty:
        st.info("لا توجد قيود مسجلة")
    else:
        sub_codes = pd.to_numeric(j["رقم الحساب الفرعي"], errors="coerce")
        subs = j[sub_codes > 0][["رقم الحساب الفرعي", "اسم صاحب الحساب"]].drop_duplicates()
        subs = subs.sort_values("رقم الحساب الفرعي")
        labels = [f"{int(r['رقم الحساب الفرعي'])} - {r['اسم صاحب الحساب']}"
                  for _, r in subs.iterrows()]
        sel = st.selectbox("اختر الحساب الفرعي (الطرف)", options=labels)
        if sel:
            code = int(sel.split(" - ")[0])
            led = db.ledger(code)
            if led.empty:
                st.info("لا توجد حركات على هذا الحساب")
            else:
                balance = led["الرصيد"].iloc[-1]
                side = "مدين" if balance > 0 else "دائن" if balance < 0 else "صفر"
                c1, c2 = st.columns(2)
                c1.metric("الرصيد الختامي", f"{abs(balance):,.2f}")
                c2.metric("طبيعة الرصيد", side)
                st.dataframe(led[["رقم القيد", "تاريخ القيد", "نوع الحركة", "رقم المرجع",
                                  "اسم الحساب", "المبلغ المدين", "المبلغ الدائن",
                                  "البيان / شرح القيد التلقائي", "الرصيد"]],
                             use_container_width=True, hide_index=True)

# =================================================================
# ملخص الفواتير
# =================================================================
with tab_inv:
    inv = db.invoices()
    if inv.empty:
        st.info("لا توجد فواتير")
    else:
        s = db.invoices_summary()
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("عدد الفواتير", s["count"])
        c2.metric("إجمالي القيمة", f"{s['total']:,.0f}")
        c3.metric("رسوم المكتب", f"{s['office_fee']:,.0f}")
        c4.metric("الزكاة", f"{s['zakat']:,.0f}")
        c5.metric("الصافي للرعوي", f"{s['net']:,.0f}")
        col_crop = db.ar_col(db.SH_INVOICES, "CropType")
        col_total = db.ar_col(db.SH_INVOICES, "TotalAmount")
        col_qty = db.ar_col(db.SH_INVOICES, "Qty")
        if col_crop and col_total:
            st.subheader("الإجماليات حسب المحصول")
            g = inv.groupby(col_crop).agg(
                عدد_الفواتير=(col_crop, "count"),
                إجمالي_الكمية=(col_qty, "sum") if col_qty else (col_total, "count"),
                إجمالي_القيمة=(col_total, "sum"),
            ).reset_index()
            st.dataframe(g, use_container_width=True, hide_index=True)
