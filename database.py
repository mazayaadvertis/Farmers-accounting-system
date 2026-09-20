"""
طبقة الوصول للبيانات — نظام المحاسبة الزراعية
جميع القراءات/الكتابات تتم على ملف Excel مع نسخ احتياطي تلقائي قبل كل كتابة
والحفاظ على بنية الجداول كما هي (صف أسماء الحقول الإنجليزي + الأعمدة غير المسماة).
"""
import os
import shutil
from datetime import datetime

import pandas as pd
import streamlit as st

EXCEL_FILE = os.environ.get("ACCOUNTING_DB", "MainDBapp.xlsx")
BACKUP_DIR = "BKUPDB"

# أسماء الأوراق
SH_INVOICES = "TableInvoices"
SH_FARMERS = "TableFarmers"
SH_BUYERS = "TableBuyers"
SH_EMPLOYEES = "TableEmployees"
SH_JOURNAL = "TableJournalEntries"
SH_PAYMENTS = "TablePayments"
SH_ACCOUNTS = "TableAccounts"
SH_USERS = "TableUsers"

# أعمدة ورقة المستخدمين (رأس عربي + صف الحقول الإنجليزي)
UC_ID = "كود المستخدم"
UC_USERNAME = "اسم المستخدم"
UC_FULLNAME = "الاسم الكامل"
UC_PASSWORD = "كلمة المرور (مشفّرة)"
UC_EMAIL = "البريد الإلكتروني"
UC_PHONE = "رقم الهاتف"
UC_ROLE = "الصلاحية"
UC_STATUS = "الحالة"
UC_CREATED = "تاريخ الإنشاء"
UC_LASTLOGIN = "آخر تسجيل دخول"
USER_COLS_AR = [UC_ID, UC_USERNAME, UC_FULLNAME, UC_PASSWORD, UC_EMAIL,
                UC_PHONE, UC_ROLE, UC_STATUS, UC_CREATED, UC_LASTLOGIN]
USER_COLS_EN = ["UserID", "Username", "FullName", "PasswordHash", "Email",
                "Phone", "Role", "Status", "CreatedAt", "LastLogin"]

# حسابات شجرة الحسابات الثابتة المستخدمة في القيود التلقائية
ACC_CASH_MAIN = 1111            # الصندوق الرئيسي
ACC_BUYERS_MAIN = 1121          # حسابات المشترين (تجميعي)
ACC_FARMERS_MAIN = 2111         # امانات المزارعين (تجميعي)
ACC_ZAKAT_MAIN = 21121          # امانات الزكاه (محصلين الزكاه)
ACC_OFFICE_INCOME = 4111        # إيراد عمولة وساطة مبيعات (5%)
ACC_BROKER_INCOME = 4121        # إيراد رسوم دلالة


# -----------------------------------------------------------------------------
# قراءة عامة مع كشف صف أسماء الحقول الإنجليزي
# -----------------------------------------------------------------------------
@st.cache_data(ttl=30)
def load_raw(sheet):
    return pd.read_excel(EXCEL_FILE, sheet_name=sheet)


def split_field_row(df):
    """يفصل صف أسماء الحقول الإنجليزي (إن وجد) ويعيد (بيانات, خريطة عربي->إنجليزي)."""
    if df.empty:
        return df, None
    first = df.iloc[0, 0]
    if isinstance(first, str) and first.strip() and not _is_number(first):
        en_map = {col: str(df.iloc[0][col]) for col in df.columns}
        return df.iloc[1:].reset_index(drop=True), en_map
    return df, None


@st.cache_data(ttl=30)
def sheet_data(sheet):
    """صفوف البيانات الفعلية (بدون صف الحقول الإنجليزي) + خريطة الأعمدة."""
    df = load_raw(sheet)
    return split_field_row(df)


def _is_number(v):
    try:
        float(str(v).strip())
        return True
    except (ValueError, TypeError):
        return False


def data_rows(sheet):
    return sheet_data(sheet)[0]


def en_map(sheet):
    return sheet_data(sheet)[1] or {}


def ar_col(sheet, english_name):
    """العمود العربي المقابل لاسم الحقل الإنجليزي (بمقارنة مرنة)."""
    for ar, en in en_map(sheet).items():
        if str(en).strip() == str(english_name).strip():
            return ar
    return None


# -----------------------------------------------------------------------------
# كتابة عامة (مع نسخ احتياطي والحفاظ على البنية)
# -----------------------------------------------------------------------------
def _backup():
    if not os.path.exists(EXCEL_FILE):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(EXCEL_FILE, os.path.join(BACKUP_DIR, f"MainDBapp_backup_{ts}.xlsx"))


def _write_sheet(df, sheet):
    try:
        if os.path.exists(EXCEL_FILE):
            with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
                df.to_excel(w, sheet_name=sheet, index=False)
        else:
            with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="w") as w:
                df.to_excel(w, sheet_name=sheet, index=False)
    except PermissionError:
        raise RuntimeError("ملف Excel مفتوح في برنامج آخر، أغلقه ثم أعد المحاولة")
    st.cache_data.clear()


def append_rows(sheet, new_df):
    """إلحاق صفوف جديدة مع الحفاظ على صف الحقول الإنجليزي والأعمدة غير المسماة."""
    _backup()
    raw = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
    new_df = new_df.reindex(columns=raw.columns)
    _write_sheet(pd.concat([raw, new_df], ignore_index=True), sheet)


def replace_rows_by_id(sheet, id_col, row_id, new_df):
    """استبدال صفوف لها نفس المعرّف (لتعديل القيود) مع الحفاظ على الرأس الإنجليزي."""
    _backup()
    raw = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
    _, e_map = split_field_row(raw)
    n_head = 1 if e_map else 0
    head = raw.iloc[:n_head]
    body = raw.iloc[n_head:]
    body_ids = pd.to_numeric(body[id_col], errors="coerce")
    try:
        target = float(row_id)
    except (ValueError, TypeError):
        target = None
    body = body[~(body_ids == target)] if target is not None else body
    new_df = new_df.reindex(columns=raw.columns)
    _write_sheet(pd.concat([head, body, new_df], ignore_index=True), sheet)


def next_id(sheet, col):
    data = data_rows(sheet)
    if data.empty or col not in data.columns:
        return 1
    vals = pd.to_numeric(data[col], errors="coerce")
    m = vals.max()
    return int(m) + 1 if pd.notna(m) else 1


# -----------------------------------------------------------------------------
# الجداول الرئيسية
# -----------------------------------------------------------------------------
def invoices():
    return data_rows(SH_INVOICES)


def farmers():
    return data_rows(SH_FARMERS)


def buyers():
    return data_rows(SH_BUYERS)


def employees():
    return data_rows(SH_EMPLOYEES)


def journal():
    return data_rows(SH_JOURNAL)


def payments():
    return data_rows(SH_PAYMENTS)


def accounts():
    return data_rows(SH_ACCOUNTS)


def users():
    return data_rows(SH_USERS)


# -----------------------------------------------------------------------------
# المستخدمون
# -----------------------------------------------------------------------------
def ensure_users_sheet():
    """ينشئ ورقة TableUsers ببنية موحدة (رأس عربي + صف الحقول الإنجليزية) إن لم تكن موجودة."""
    if SH_USERS in pd.ExcelFile(EXCEL_FILE).sheet_names:
        return False
    _backup()
    _write_sheet(pd.DataFrame([USER_COLS_EN], columns=USER_COLS_AR), SH_USERS)
    return True


def update_user(user_id, **fields):
    """تعديل حقول مستخدم حسب كوده (مثل كلمة المرور أو آخر تسجيل دخول)."""
    raw = pd.read_excel(EXCEL_FILE, sheet_name=SH_USERS)
    mask = pd.to_numeric(raw[UC_ID], errors="coerce") == float(user_id)
    if not mask.any():
        return False
    _backup()
    for col, val in fields.items():
        raw.loc[mask, col] = val
    _write_sheet(raw, SH_USERS)
    return True


# -----------------------------------------------------------------------------
# الأطراف (مزارعون / مشترون / موظفون)
# -----------------------------------------------------------------------------
def _clean_code(v):
    try:
        return int(float(str(v).strip()))
    except (ValueError, TypeError):
        return None


def entity_lists():
    """قوائم منسدلة بصيغة: كود - اسم (نوع)"""
    out = {}
    for key, df, code_col, name_col, label in [
        ("farmers", farmers(), "رقم الحساب", "اسم المزارع", "مزارع"),
        ("buyers", buyers(), "رقم حساب المشتري", "اسم المشتري", "مشتري"),
        ("employees", employees(), "كود الموظف", "اسم الموظف", "موظف"),
    ]:
        items = []
        for _, r in df.iterrows():
            code = _clean_code(r.get(code_col))
            name = str(r.get(name_col, "")).strip()
            if code and name and name.lower() != "nan":
                items.append((code, name, f"{code} - {name} ({label})"))
        out[key] = items
    return out


def employees_by_role(keyword):
    df = employees()
    mask = df["الصفة / الوظيفة"].astype(str).str.contains(keyword, na=False)
    return df[mask]


def roles_list():
    df = employees()
    return sorted(df["الصفة / الوظيفة"].astype(str).unique())


# -----------------------------------------------------------------------------
# شجرة الحسابات
# -----------------------------------------------------------------------------
def sub_accounts():
    df = accounts()
    return df[(df["حساب حركة (قابل للترحيل)"] == "نعم") & (df["الحالة"] == "نشط")]


def cash_accounts():
    df = accounts()
    codes = df["رقم الحساب"].astype(str)
    return df[(codes.str.startswith("111")) & (df["حساب حركة (قابل للترحيل)"] == "نعم")]


def account_options(df=None):
    df = sub_accounts() if df is None else df
    return [f"{int(r['رقم الحساب'])} - {r['اسم الحساب']}" for _, r in df.iterrows()]


def find_account(code):
    df = accounts()
    m = df[pd.to_numeric(df["رقم الحساب"], errors="coerce") == float(code)]
    return m.iloc[0] if not m.empty else None


def search_accounts(term):
    df = accounts()
    term = str(term).strip()
    if not term:
        return df
    return df[
        df["رقم الحساب"].astype(str).str.contains(term, case=False, na=False)
        | df["اسم الحساب"].astype(str).str.contains(term, case=False, na=False)
    ]


def add_account(code, name, parent_code, level, acc_type, nature, is_sub, currency, is_active):
    df = accounts()
    if pd.to_numeric(df["رقم الحساب"], errors="coerce").eq(float(code)).any():
        return False, "رقم الحساب موجود مسبقاً!"
    new_row = pd.DataFrame([{
        "رقم الحساب": int(code),
        "اسم الحساب": name,
        "الحساب الأب": int(parent_code) if parent_code else 0,
        "المستوى": int(level),
        "نوع الحساب": acc_type,
        "طبيعة الحساب": nature,
        "حساب حركة (قابل للترحيل)": is_sub,
        "العملة": currency,
        "الحالة": is_active,
    }])
    append_rows(SH_ACCOUNTS, new_row)
    return True, "تمت إضافة الحساب بنجاح"


def update_account(code, name, parent_code, level, acc_type, nature, is_sub, currency, is_active):
    raw = pd.read_excel(EXCEL_FILE, sheet_name=SH_ACCOUNTS)
    mask = pd.to_numeric(raw["رقم الحساب"], errors="coerce") == float(code)
    if not mask.any():
        return False, "الحساب غير موجود!"
    _backup()
    raw.loc[mask, "اسم الحساب"] = name
    raw.loc[mask, "الحساب الأب"] = parent_code
    raw.loc[mask, "المستوى"] = level
    raw.loc[mask, "نوع الحساب"] = acc_type
    raw.loc[mask, "طبيعة الحساب"] = nature
    raw.loc[mask, "حساب حركة (قابل للترحيل)"] = is_sub
    raw.loc[mask, "العملة"] = currency
    raw.loc[mask, "الحالة"] = is_active
    _write_sheet(raw, SH_ACCOUNTS)
    return True, "تم تعديل بيانات الحساب بنجاح"


# -----------------------------------------------------------------------------
# القيود اليومية
# -----------------------------------------------------------------------------
def save_journal_entry(entry_id, entry_date, trans_type, ref_no, rows_data):
    """rows_data: قائمة dict فيها main_code, main_name, sub_code, sub_name, debit, credit, desc"""
    tot_dr = sum(float(r["debit"]) for r in rows_data)
    tot_cr = sum(float(r["credit"]) for r in rows_data)
    if round(tot_dr, 2) != round(tot_cr, 2):
        return False, f"القيد غير متوازن! مدين ({tot_dr:,.2f}) ≠ دائن ({tot_cr:,.2f})"
    if tot_dr == 0:
        return False, "لا يمكن حفظ قيد بمبالغ صفرية"

    try:
        dt = pd.to_datetime(f"{entry_date}", errors="raise")
    except (ValueError, TypeError):
        dt = str(entry_date)

    cols = list(load_raw(SH_JOURNAL).columns)
    new_rows = pd.DataFrame([
        {
            "رقم القيد": entry_id,
            "تاريخ القيد": dt,
            "نوع الحركة": trans_type,
            "رقم المرجع": ref_no,
            "رقم الحساب الرئيسي": r["main_code"],
            "اسم الحساب": r["main_name"],
            "رقم الحساب الفرعي": r["sub_code"],
            "اسم صاحب الحساب": r["sub_name"],
            "المبلغ المدين": r["debit"],
            "المبلغ الدائن": r["credit"],
            "البيان / شرح القيد التلقائي": r["desc"],
            "بيان فرعي": r.get("sub_desc", ""),
        }
        for r in rows_data
    ]).reindex(columns=cols)

    replace_rows_by_id(SH_JOURNAL, "رقم القيد", entry_id, new_rows)
    return True, f"تم حفظ وتوجيه القيد رقم ({entry_id}) بنجاح"


# -----------------------------------------------------------------------------
# الفواتير
# -----------------------------------------------------------------------------
def append_invoice(values_en):
    """
    إلحاق فاتورة جديدة. values_en: dict بأسماء الحقول الإنجليزية
    (مطابقة لصف أسماء الحقول في الورقة) — تُترجم تلقائياً للأعمدة العربية.
    """
    raw = load_raw(SH_INVOICES)
    _, e_map = split_field_row(raw)
    row = {}
    for ar_col_name in raw.columns:
        en_name = e_map.get(ar_col_name) if e_map else None
        row[ar_col_name] = values_en.get(en_name) if en_name else None
    append_rows(SH_INVOICES, pd.DataFrame([row]))
    return True, "تم حفظ الفاتورة بنجاح"


# -----------------------------------------------------------------------------
# سندات القبض والصرف
# -----------------------------------------------------------------------------
def append_payment(values_ar):
    """إلحاق سند دفع. values_ar: dict بالأعمدة العربية لورقة TablePayments."""
    raw = load_raw(SH_PAYMENTS)
    row = {c: values_ar.get(c) for c in raw.columns}
    append_rows(SH_PAYMENTS, pd.DataFrame([row]))
    return True, "تم حفظ السند بنجاح"


# -----------------------------------------------------------------------------
# التقارير
# -----------------------------------------------------------------------------
def trial_balance():
    j = journal().copy()
    if j.empty:
        return j
    j["_dr"] = pd.to_numeric(j["المبلغ المدين"], errors="coerce").fillna(0)
    j["_cr"] = pd.to_numeric(j["المبلغ الدائن"], errors="coerce").fillna(0)
    g = j.groupby(["رقم الحساب الرئيسي", "اسم الحساب"], dropna=False)[["_dr", "_cr"]].sum().reset_index()
    g["الرصيد (مدين - دائن)"] = g["_dr"] - g["_cr"]
    g = g.rename(columns={"_dr": "إجمالي مدين", "_cr": "إجمالي دائن"})
    return g.sort_values("رقم الحساب الرئيسي", key=lambda s: pd.to_numeric(s, errors="coerce"))


def ledger(sub_code):
    j = journal().copy()
    if j.empty:
        return j
    code_num = pd.to_numeric(j["رقم الحساب الفرعي"], errors="coerce")
    entries = j[code_num == float(sub_code)].copy()
    if entries.empty:
        return entries
    entries["_dr"] = pd.to_numeric(entries["المبلغ المدين"], errors="coerce").fillna(0)
    entries["_cr"] = pd.to_numeric(entries["المبلغ الدائن"], errors="coerce").fillna(0)
    entries = entries.sort_values("رقم القيد")
    entries["الرصيد"] = (entries["_dr"] - entries["_cr"]).cumsum()
    return entries.drop(columns=["_dr", "_cr"])


def journal_is_balanced():
    j = journal()
    if j.empty:
        return True, 0.0
    dr = pd.to_numeric(j["المبلغ المدين"], errors="coerce").fillna(0).sum()
    cr = pd.to_numeric(j["المبلغ الدائن"], errors="coerce").fillna(0).sum()
    return abs(dr - cr) < 0.01, float(dr - cr)


def invoices_summary():
    inv = invoices()
    if inv.empty:
        return {}
    out = {"count": len(inv)}
    for key, en_name in [
        ("total", "TotalAmount"),
        ("office_fee", "OfficeFee"),
        ("zakat", "Zakat"),
        ("paid", "PaidAmount"),
        ("net", "NetFarmer"),
    ]:
        col = ar_col(SH_INVOICES, en_name)
        out[key] = float(pd.to_numeric(inv[col], errors="coerce").fillna(0).sum()) if col else 0.0
    return out
