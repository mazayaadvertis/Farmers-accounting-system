"""
🧾 فاتورة مزارع جديدة
إدخال فاتورة بيع محصول مع الحسابات التلقائية (عمولة المكتب 5% والزكاة 4%)
وخيار توليد القيد المحاسبي التلقائي المتوازن.
"""
from datetime import datetime

import pandas as pd
import streamlit as st

import auth
import database as db
from ui import page_header

auth.require_login()
page_header("فاتورة مزارع جديدة", "🧾")

ADD_NEW = "➕ إضافة جديد..."

entities = db.entity_lists()
farmers_items = entities["farmers"]      # [(code, name, label)]
buyers_items = entities["buyers"]
farmers_df = db.farmers()
buyers_df = db.buyers()

brokers = db.employees_by_role("دلال")
collectors = db.employees_by_role("زكاة")
cash_opts = db.account_options(db.cash_accounts())
if not cash_opts:
    cash_opts = db.account_options(db.sub_accounts())

# =================================================================
# 1) البيانات الأساسية
# =================================================================
with st.expander("البيانات الأساسية للفاتورة", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        invoice_no = st.number_input("رقم الفاتورة", min_value=1, step=1,
                                     value=db.next_id(db.SH_INVOICES, "رقم الفاتورة"))
        more_options = st.checkbox("خيارات اكثر")
    with c2:
        invoice_date = st.date_input("تاريخ الفاتورة", datetime.today())
    with c3:
        invoice_time = st.time_input("وقت ادخال الفاتورة", datetime.now().time())
    with c4:
        broker_name = st.selectbox("الدلال", options=[""] + brokers["اسم الموظف"].tolist())

# =================================================================
# 2) الأطراف
# =================================================================
with st.expander("بيانات الأطراف (الرعوي والمشتري)", expanded=True):
    c1, c2 = st.columns(2)

    farmer_options = [it[2] for it in farmers_items] + [ADD_NEW]
    with c1:
        sel_farmer = st.selectbox("اسم الرعوي (المزارع)", options=farmer_options)
        new_farmer_name = ""
        if sel_farmer == ADD_NEW:
            new_farmer_name = st.text_input("اسم الرعوي الجديد (الرباعي الكامل)")
        farmer_code, farmer_name, farmer_phone, office_pct, zakat_pct, farmer_crop = 0, "", "", 0.05, 0.04, ""
        if sel_farmer != ADD_NEW:
            farmer_code = int(sel_farmer.split(" - ")[0])
            row = farmers_df[pd.to_numeric(farmers_df["رقم الحساب"], errors="coerce") == farmer_code]
            if not row.empty:
                r = row.iloc[0]
                farmer_name = str(r["اسم المزارع"])
                ph = pd.to_numeric(pd.Series([r.get("رقم الهاتف الرئيسي")]), errors="coerce").iloc[0]
                farmer_phone = "" if pd.isna(ph) else str(int(ph))
                op = pd.to_numeric(pd.Series([r.get("نسبة عمولة المكتب له")]), errors="coerce").iloc[0]
                zp = pd.to_numeric(pd.Series([r.get("نسبة الزكاة")]), errors="coerce").iloc[0]
                office_pct = float(op) if pd.notna(op) and op > 0 else 0.05
                zakat_pct = float(zp) if pd.notna(zp) and zp > 0 else 0.04
                farmer_crop = str(r.get("أهم المحاصيل", ""))
                if farmer_crop.lower() == "nan":
                    farmer_crop = ""
        farmer_phone_in = st.text_input("رقم تلفون الرعوي", value=farmer_phone)
        crop_type = st.text_input("نوع المحصول", value=farmer_crop)

    buyer_options = [it[2] for it in buyers_items] + [ADD_NEW]
    with c2:
        sel_buyer = st.selectbox("اسم المشتري", options=buyer_options)
        new_buyer_name = ""
        if sel_buyer == ADD_NEW:
            new_buyer_name = st.text_input("اسم المشتري الجديد")
        buyer_code, buyer_name, buyer_phone, buyer_guarantor = 0, "", "", ""
        if sel_buyer != ADD_NEW:
            buyer_code = int(sel_buyer.split(" - ")[0])
            row = buyers_df[pd.to_numeric(buyers_df["رقم حساب المشتري"], errors="coerce") == buyer_code]
            if not row.empty:
                r = row.iloc[0]
                buyer_name = str(r["اسم المشتري"])
                ph = pd.to_numeric(pd.Series([r.get("رقم تلفون المشتري")]), errors="coerce").iloc[0]
                buyer_phone = "" if pd.isna(ph) else str(int(ph))
                g = str(r.get("اسم الضمين على المشتري", ""))
                buyer_guarantor = "" if g.lower() == "nan" else g
        buyer_phone_in = st.text_input("رقم تلفون المشتري", value=buyer_phone)
        guarantor_in = st.text_input("الضمين على المشتري", value=buyer_guarantor)

# =================================================================
# 3) الكميات والأسعار
# =================================================================
with st.expander("الكميات والأسعار والنسب", expanded=True):
    c1, c2, c3, c4, c5 = st.columns(5)
    qty = c1.number_input("العدد (الكمية)", min_value=0.0, value=0.0, step=1.0)
    price = c2.number_input("السعر للوحدة", min_value=0.0, value=0.0, step=100.0)
    broker_fee = c3.number_input("الدلاله (للوحدة)", min_value=0.0, value=100.0, step=50.0)
    office_pct_in = c4.number_input("نسبة رسوم المكتب", min_value=0.0, value=float(office_pct), step=0.01, format="%.4f")
    zakat_pct_in = c5.number_input("نسبة الزكاة", min_value=0.0, value=float(zakat_pct), step=0.01, format="%.4f")

# =================================================================
# 4) تكاليف إضافية (اختياري)
# =================================================================
with st.expander("تكاليف إضافية (على الرعوي / على المشتري)", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        has_farmer_costs = st.checkbox("هل يوجد تكلفة على الرعوي؟")
        farmer_unit_cost = st.number_input("التكلفة للوحدة (على الرعوي)", min_value=0.0, value=0.0) if has_farmer_costs else 0.0
        farmer_cost_type = st.text_input("نوع التكلفة (على الرعوي)") if has_farmer_costs else ""
    with c2:
        has_buyer_costs = st.checkbox("هل يوجد تكلفة على المشتري؟")
        buyer_unit_cost = st.number_input("التكلفة للوحدة (على المشتري)", min_value=0.0, value=0.0) if has_buyer_costs else 0.0
        buyer_cost_type = st.text_input("نوع التكلفة (على المشتري)") if has_buyer_costs else ""

# =================================================================
# الحسابات التلقائية
# =================================================================
total_value = qty * price
total_broker_fee = qty * broker_fee
office_fee = total_value * office_pct_in
zakat_amount = total_value * zakat_pct_in
after_office = total_value - office_fee
net_farmer = after_office - zakat_amount
farmer_total_costs = qty * farmer_unit_cost if has_farmer_costs else 0.0
net_after_farmer_costs = net_farmer - farmer_total_costs
buyer_total_costs = qty * buyer_unit_cost if has_buyer_costs else 0.0
total_on_buyer = total_value + total_broker_fee + buyer_total_costs

c1, c2, c3, c4 = st.columns(4)
c1.metric("إجمالي القيمة", f"{total_value:,.2f}")
c2.metric(f"رسوم المكتب ({office_pct_in:.2%})", f"{office_fee:,.2f}")
c3.metric(f"الزكاة ({zakat_pct_in:.2%})", f"{zakat_amount:,.2f}")
c4.metric("صافي مستحق الرعوي", f"{net_after_farmer_costs:,.2f}")

# =================================================================
# 5) الدفع والصندوق
# =================================================================
with st.expander("تفاصيل الدفع والصندوق", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        receiving_box = st.selectbox("صندوق الاستلام", options=cash_opts)
        collector_name = st.selectbox("محصل الزكاة", options=[""] + collectors["اسم الموظف"].tolist())
    with c2:
        paid_amount = st.number_input("المبلغ المدفوع", min_value=0.0, value=0.0, step=1000.0)
        payor_default = buyer_name if buyer_name else "المشتري"
        paid_by = st.text_input("مدفوع من", value=payor_default)
    with c3:
        payment_method = st.selectbox("طريقة الدفع", ["نقداً", "حوالة مصرفية", "شبكة صرافة", "آجل"])
        payment_note = st.text_area("ملاحظة الدفع / الفاتورة")

remaining = net_after_farmer_costs - paid_amount
st.info(f"إجمالي الفاتورة على المشتري: **{total_on_buyer:,.2f}** — الباقي من صافي الرعوي بعد الدفع: **{remaining:,.2f}**")

# =================================================================
# خيارات إضافية (وكيل الرعوي)
# =================================================================
agent_flag, agent_name, agent_phone = "No", "", ""
if more_options:
    with st.expander("خيارات اكثر (وكيل الرعوي / خصميات النسب)", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        transfer_to_agent = c1.checkbox("تحويل المبلغ باسم وكيل الرعوي")
        agent_flag = "Yes" if transfer_to_agent else "No"
        if transfer_to_agent:
            agent_name = c2.text_input("اسم وكيل الرعوي")
            agent_phone = c3.text_input("رقم تلفون الوكيل")
        office_ded = c4.number_input("خصم من رسوم المكتب %", min_value=0.0, value=0.0, step=0.5)
        zakat_ded = c5.number_input("خصم من الزكاة %", min_value=0.0, value=0.0, step=0.5)
else:
    office_ded, zakat_ded = 0.0, 0.0

# =================================================================
# حفظ الفاتورة + القيد التلقائي
# =================================================================
make_journal = st.checkbox("✅ توليد القيد المحاسبي التلقائي للفاتورة", value=True)

if st.button("💾 حفظ الفاتورة", type="primary", use_container_width=True):
    # إنشاء طرف جديد إن لزم
    try:
        if sel_farmer == ADD_NEW:
            if not new_farmer_name.strip():
                st.error("يرجى إدخال اسم الرعوي الجديد"); st.stop()
            farmer_code = db.next_id(db.SH_FARMERS, "رقم الحساب")
            db.append_rows(db.SH_FARMERS, pd.DataFrame([{
                "رقم الحساب": farmer_code, "اسم المزارع": new_farmer_name.strip(),
                "رقم الهاتف الرئيسي": farmer_phone_in or None,
                "نسبة عمولة المكتب له": office_pct_in, "نسبة الزكاة": zakat_pct_in,
                "أهم المحاصيل": crop_type, "حالة المزارع": 1, "تاريخ الاضافه": datetime.today(),
            }]))
            farmer_name = new_farmer_name.strip()
        if sel_buyer == ADD_NEW:
            if not new_buyer_name.strip():
                st.error("يرجى إدخال اسم المشتري الجديد"); st.stop()
            buyer_code = db.next_id(db.SH_BUYERS, "رقم حساب المشتري")
            db.append_rows(db.SH_BUYERS, pd.DataFrame([{
                "رقم حساب المشتري": buyer_code, "اسم المشتري": new_buyer_name.strip(),
                "رقم تلفون المشتري": buyer_phone_in or None,
                "اسم الضمين على المشتري": guarantor_in or None,
                "الحالة": 1, "تاريخ الاضافه": datetime.today(),
            }]))
            buyer_name = new_buyer_name.strip()

        if qty <= 0 or price <= 0:
            st.error("يرجى إدخال الكمية والسعر بشكل صحيح"); st.stop()

        values_en = {
            "InvoiceType_more_options": bool(more_options),
            "InvoiceDate": datetime.combine(invoice_date, invoice_time),
            "InvoiceTime": datetime.combine(invoice_date, invoice_time),
            "InvoiceNo": int(invoice_no),
            "CboxFarmerName": farmer_name,
            "CboxBuyerName": buyer_name,
            "Qty": qty, "Price": price, "CropType": crop_type,
            "BrokerFee": broker_fee,
            "TotalAmount": total_value,
            "OfficeFee": office_fee,
            "AfterFee": after_office,
            "Zakat": zakat_amount,
            "NetFarmer": net_after_farmer_costs,
            "PaidAmount": paid_amount,
            "RemainingFromNet": remaining,
            "BrokerName": broker_name,
            "ZakatCollectorName": collector_name,
            "FarmerPhone": farmer_phone_in,
            "BuyerPhone": buyer_phone_in,
            "PaidAmountBy": paid_by,
            "PayMethod": payment_method,
            "PayNote": payment_note,
            "BuyerGuarantor": guarantor_in,
            "CheckBoxTransferToAgentFarmer": agent_flag,
            "CBoxNameOfAgentFarmer": agent_name or None,
            "AgentPhone": agent_phone or None,
            "OfficeFeePercent": office_pct_in,
            "ZakatPercent": zakat_pct_in,
            "OfficeDeductionPercent": office_ded,
            "ZakatDeductionPercent": zakat_ded,
            "CheckBoxOtherCostsOnFramer": "Yes" if has_farmer_costs else "No",
            "UnitCostOnFarmer": farmer_unit_cost if has_farmer_costs else None,
            "FarmerTotalCosts": farmer_total_costs if has_farmer_costs else None,
            "NetAfterFarmerCosts": net_after_farmer_costs if has_farmer_costs else None,
            "CheckBoxOtherCostsOnBuyer": "Yes" if has_buyer_costs else "No",
            "UnitCostOnBuyer": buyer_unit_cost if has_buyer_costs else None,
            "TotalOtherCostsOnBuyer": buyer_total_costs if has_buyer_costs else None,
            "TypeOtherCostOnBuyer": buyer_cost_type or None,
            "TotalAmountOnBuyer": total_on_buyer,
            "Farmer_subAccountCode": farmer_code,
            "Buyer_subAccountCode": buyer_code,
            "InvoiceNote": payment_note or None,
        }
        db.append_invoice(values_en)

        if make_journal:
            acc = lambda c: db.find_account(c)
            def acc_name(code, fallback):
                r = acc(code)
                return str(r["اسم الحساب"]) if r is not None else fallback

            buyer_main_name = acc_name(db.ACC_BUYERS_MAIN, "حسابات المشترين")
            farmer_main_name = acc_name(db.ACC_FARMERS_MAIN, "امانات المزارعين")
            cash_code = int(receiving_box.split(" - ")[0]) if receiving_box else db.ACC_CASH_MAIN
            cash_name = acc_name(cash_code, "الصندوق الرئيسي")

            broker_code = 0
            if broker_name:
                brow = brokers[brokers["اسم الموظف"] == broker_name]
                if not brow.empty:
                    broker_code = db._clean_code(brow.iloc[0]["كود الموظف"]) or 0
            collector_code = 0
            if collector_name:
                crow = collectors[collectors["اسم الموظف"] == collector_name]
                if not crow.empty:
                    collector_code = db._clean_code(crow.iloc[0]["كود الموظف"]) or 0

            ref = f"فاتورة رقم {invoice_no}"
            rows = [
                {"main_code": db.ACC_BUYERS_MAIN, "main_name": buyer_main_name,
                 "sub_code": buyer_code, "sub_name": f"المشتري/{buyer_name}",
                 "debit": round(total_on_buyer, 2), "credit": 0.0, "desc": f"{ref} — إجمالي الفاتورة على المشتري"},
                {"main_code": db.ACC_FARMERS_MAIN, "main_name": farmer_main_name,
                 "sub_code": farmer_code, "sub_name": f"حساب المزارع/{farmer_name}",
                 "debit": 0.0, "credit": round(net_after_farmer_costs, 2), "desc": f"{ref} — صافي مستحق الرعوي بعد الخصميات"},
                {"main_code": db.ACC_OFFICE_INCOME, "main_name": acc_name(db.ACC_OFFICE_INCOME, "إيراد عمولة المكتب"),
                 "sub_code": 0, "sub_name": "", "debit": 0.0, "credit": round(office_fee, 2),
                 "desc": f"{ref} — إيراد عمولة وساطة {office_pct_in:.2%}"},
                {"main_code": db.ACC_ZAKAT_MAIN, "main_name": acc_name(db.ACC_ZAKAT_MAIN, "امانات الزكاه"),
                 "sub_code": collector_code, "sub_name": f"محصل الزكاة/{collector_name}" if collector_name else "",
                 "debit": 0.0, "credit": round(zakat_amount, 2), "desc": f"{ref} — أمانات مصلحة الزكاة {zakat_pct_in:.2%}"},
                {"main_code": db.ACC_BROKER_INCOME, "main_name": acc_name(db.ACC_BROKER_INCOME, "إيراد رسوم دلالة"),
                 "sub_code": broker_code, "sub_name": f"الدلال/{broker_name}" if broker_name else "",
                 "debit": 0.0, "credit": round(total_broker_fee, 2), "desc": f"{ref} — إيراد رسوم دلالة"},
            ]
            if farmer_total_costs > 0:
                cost_acc = 2132
                rows.append({"main_code": cost_acc, "main_name": acc_name(cost_acc, "مصروفات مستحقة الدفع"),
                             "sub_code": 0, "sub_name": "",
                             "debit": 0.0, "credit": round(farmer_total_costs, 2),
                             "desc": f"{ref} — تكاليف على الرعوي: {farmer_cost_type}"})
            if buyer_total_costs > 0:
                svc_acc = 4122
                rows.append({"main_code": svc_acc, "main_name": acc_name(svc_acc, "إيرادات خدمات"),
                             "sub_code": 0, "sub_name": "",
                             "debit": 0.0, "credit": round(buyer_total_costs, 2),
                             "desc": f"{ref} — تكاليف على المشتري: {buyer_cost_type}"})
            if paid_amount > 0:
                rows.append({"main_code": cash_code, "main_name": cash_name, "sub_code": 0, "sub_name": "",
                             "debit": round(paid_amount, 2), "credit": 0.0,
                             "desc": f"{ref} — المبلغ المحصل نقداً ({payment_method})"})
                rows.append({"main_code": db.ACC_BUYERS_MAIN, "main_name": buyer_main_name,
                             "sub_code": buyer_code, "sub_name": f"المشتري/{buyer_name}",
                             "debit": 0.0, "credit": round(paid_amount, 2),
                             "desc": f"{ref} — تسوية المدفوع من ذمة المشتري"})

            entry_id = db.next_id(db.SH_JOURNAL, "رقم القيد")
            ok, jmsg = db.save_journal_entry(entry_id, invoice_date, "فاتورة مزارع", ref, rows)
            if ok:
                st.success(f"تم حفظ الفاتورة رقم {invoice_no} وتوليد القيد المحاسبي رقم {entry_id}")
            else:
                st.warning(f"تم حفظ الفاتورة رقم {invoice_no}، لكن توليد القيد فشل: {jmsg}")
        else:
            st.success(f"تم حفظ الفاتورة رقم {invoice_no} بنجاح")
        st.balloons()
        st.rerun()
    except RuntimeError as e:
        st.error(str(e))

# =================================================================
# سجل الفواتير
# =================================================================
st.markdown("---")
st.subheader("📋 سجل الفواتير")
inv_df = db.invoices()
if inv_df.empty:
    st.info("لا توجد فواتير")
else:
    show_cols = [c for c in [
        db.ar_col(db.SH_INVOICES, "InvoiceNo"), db.ar_col(db.SH_INVOICES, "InvoiceDate"),
        db.ar_col(db.SH_INVOICES, "CboxFarmerName"), db.ar_col(db.SH_INVOICES, "CboxBuyerName"),
        db.ar_col(db.SH_INVOICES, "Qty"), db.ar_col(db.SH_INVOICES, "Price"),
        db.ar_col(db.SH_INVOICES, "TotalAmount"), db.ar_col(db.SH_INVOICES, "NetFarmer"),
        db.ar_col(db.SH_INVOICES, "PaidAmount"),
    ] if c]
    st.dataframe(inv_df[show_cols].iloc[::-1], use_container_width=True, hide_index=True)
