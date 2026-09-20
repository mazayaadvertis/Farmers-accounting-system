"""
النظام المحاسبي الزراعي — الصفحة الرئيسية
لوحة تحكم بمؤشرات الأداء والأرصدة والتنقل بين الوحدات.
التشغيل:  streamlit run accounting_app.py
"""
import streamlit as st

import auth
import database as db
from ui import page_setup

if not auth.is_logged_in():
    auth.render_auth_page()
    st.stop()

page_setup("النظام المحاسبي الزراعي")
auth.sidebar_user_box()

# ---------------------------------------------------------------- KPIs
inv = db.invoices_summary()
balanced, diff = db.journal_is_balanced()

c1, c2, c3, c4 = st.columns(4)
c1.metric("عدد الفواتير", inv.get("count", 0))
c2.metric("إجمالي قيمة الفواتير", f"{inv.get('total', 0):,.0f} ريال")
c3.metric("إجمالي رسوم المكتب (5%)", f"{inv.get('office_fee', 0):,.0f} ريال")
c4.metric("إجمالي الزكاة (4%)", f"{inv.get('zakat', 0):,.0f} ريال")

c5, c6, c7, c8 = st.columns(4)
c5.metric("المزارعون", len(db.farmers()))
c6.metric("المشترون", len(db.buyers()))
c7.metric("الموظفون", len(db.employees()))
c8.metric("عدد الحسابات", len(db.accounts()))

if balanced:
    st.success("✅ قيود اليومية متوازنة (إجمالي المدين = إجمالي الدائن)")
else:
    st.error(f"⚠️ قيود اليومية غير متوازنة — فرق بمقدار {diff:,.2f} ريال")

st.markdown("---")

# ---------------------------------------------------------------- recent invoices
st.subheader("🧾 أحدث الفواتير")
inv_df = db.invoices()
if inv_df.empty:
    st.info("لا توجد فواتير مسجلة بعد")
else:
    col_no = db.ar_col(db.SH_INVOICES, "InvoiceNo")
    col_date = db.ar_col(db.SH_INVOICES, "InvoiceDate")
    col_farmer = db.ar_col(db.SH_INVOICES, "CboxFarmerName")
    col_buyer = db.ar_col(db.SH_INVOICES, "CboxBuyerName")
    col_total = db.ar_col(db.SH_INVOICES, "TotalAmount")
    cols = [c for c in [col_no, col_date, col_farmer, col_buyer, col_total] if c]
    recent = inv_df[cols].tail(8).iloc[::-1]
    st.dataframe(recent, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- module guide
st.markdown("---")
st.subheader("📚 وحدات النظام")
st.markdown("""
| الصفحة | الوظيفة |
|---|---|
| 🧾 فاتورة مزارع جديدة | إدخال فواتير البيع مع الحسابات التلقائية وتوليد القيد المحاسبي |
| 📑 قيود اليومية | استعراض وتسجيل القيود اليدوية مع التحقق من التوازن |
| 💰 سندات القبض والصرف | تسجيل حركات النقدية وتوليد قيودها المحاسبية |
| 🌳 شجرة الحسابات | دليل الحسابات — إضافة وتعديل وبحث |
| 👥 الأطراف والموظفون | إدارة المزارعين والمشترين والموظفين والأدوار المالية |
| 📊 التقارير المالية | ميزان المراجعة وكشوف الحسابات وملخص الفواتير |
""")
