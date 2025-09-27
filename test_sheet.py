# app.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="Clinic Finance Tracker", layout="wide")

# -------- CONFIG --------
SPREADSHEET_NAME = "PatientPayments"     # the spreadsheet you created & shared with the service account
PAYMENTS_WS_TITLE = "Payments"           # worksheet for patient payments (will be created if missing)
EXPENSES_WS_TITLE = "Expenses"           # worksheet for expenses (will be created if missing)

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

PAYMENT_COLS = ["Patient Name", "Amount Paid", "Date", "Notes"]
EXPENSE_COLS = ["Expense Name", "Amount", "Date", "Notes"]

# -------- AUTHENTICATION --------
@st.cache_resource(ttl=3600)
def gsheet_client():
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        st.error("Error authorizing Google Sheets. Check your secrets and private key formatting.")
        st.stop()

client = gsheet_client()

# -------- UTIL: worksheet get-or-create & load/save helpers --------
def get_or_create_ws(spreadsheet, title, headers):
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        ws.append_row(headers)
    return ws

def open_spreadsheet(name):
    try:
        return client.open(name)
    except Exception as e:
        st.error(f"Could not open spreadsheet '{name}'. Make sure it's shared with the service account and the name is exact.")
        st.stop()

def load_sheet_df(ws, expected_cols):
    try:
        records = ws.get_all_records()
    except Exception as e:
        st.error(f"Error reading worksheet '{ws.title}': {e}")
        return pd.DataFrame(columns=expected_cols)

    if not records:
        return pd.DataFrame(columns=expected_cols)

    df = pd.DataFrame(records)

    # Ensure expected columns exist (in case of capitalization differences)
    for c in expected_cols:
        if c not in df.columns:
            df[c] = ""

    # Normalize column order
    df = df[expected_cols]

    # Ensure numeric conversion for amount columns
    amt_col = expected_cols[1]
    df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0.0)

    # Convert Date to python date objects for easy comparison
    date_col = expected_cols[2]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date

    return df

def append_row(ws, row_values):
    try:
        ws.append_row(row_values)
    except Exception as e:
        st.error(f"Could not append row to '{ws.title}': {e}")

def update_row(ws, sheet_row_idx, values):
    # sheet_row_idx is actual sheet row index (1-based)
    try:
        # assume 4 columns A:D
        ws.update(f"A{sheet_row_idx}:D{sheet_row_idx}", [values])
    except Exception as e:
        st.error(f"Could not update row {sheet_row_idx} on '{ws.title}': {e}")

def delete_row(ws, sheet_row_idx):
    try:
        ws.delete_rows(sheet_row_idx)
    except Exception as e:
        st.error(f"Could not delete row {sheet_row_idx} on '{ws.title}': {e}")

# -------- PREP: open spreadsheet and worksheets --------
spreadsheet = open_spreadsheet(SPREADSHEET_NAME)
ws_payments = get_or_create_ws(spreadsheet, PAYMENTS_WS_TITLE, PAYMENT_COLS)
ws_expenses = get_or_create_ws(spreadsheet, EXPENSES_WS_TITLE, EXPENSE_COLS)

# -------- SIMPLE LOGIN (optional) --------
# Remove or change the username/password as you like
USERNAME = "irisclinic"
PASSWORD = "welcome01"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_screen():
    st.title("🔐 Login to Iris Clinic App")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == USERNAME and p == PASSWORD:
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

# -------- MAIN APP UI --------
def main_app():
    st.title("🏥 Clinic Finance Tracker")

    # Load fresh data from sheets
    df_payments = load_sheet_df(ws_payments, PAYMENT_COLS)
    df_expenses = load_sheet_df(ws_expenses, EXPENSE_COLS)

    # --- Layout: two columns for add forms ---
    col1, col2 = st.columns(2)
    with col1:
        st.header("➕ Add Payment")
        with st.form("add_payment_form", clear_on_submit=True):
            p_name = st.text_input("Patient Name")
            p_amount = st.number_input("Amount Paid", min_value=0.0, step=0.01, format="%.2f")
            p_date = st.date_input("Date", value=datetime.today().date())
            p_notes = st.text_area("Notes (optional)")
            if st.form_submit_button("Add Payment"):
                if not p_name.strip():
                    st.error("Patient Name cannot be empty.")
                else:
                    append_row(ws_payments, [p_name, float(p_amount), p_date.isoformat(), p_notes])
                    st.success("Payment added.")
                    st.experimental_rerun()

    with col2:
        st.header("➕ Add Expense")
        with st.form("add_expense_form", clear_on_submit=True):
            e_name = st.text_input("Expense Name")
            e_amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")
            e_date = st.date_input("Date", value=datetime.today().date())
            e_notes = st.text_area("Notes (optional)")
            if st.form_submit_button("Add Expense"):
                if not e_name.strip():
                    st.error("Expense Name cannot be empty.")
                else:
                    append_row(ws_expenses, [e_name, float(e_amount), e_date.isoformat(), e_notes])
                    st.success("Expense added.")
                    st.experimental_rerun()

    st.markdown("---")

    # ---------- PAYMENTS SECTION ----------
    st.header("💳 Patient Payments")

    def payments_filter_ui(df):
        if df.empty:
            st.info("No payments yet.")
            return df
        with st.expander("🔎 Filters (Payments)"):
            name_filter = st.text_input("Filter by Patient Name", key="pf_name")
            # Date range default: min and max or today
            min_dt = df["Date"].min() if df["Date"].notna().any() else datetime.today().date()
            max_dt = df["Date"].max() if df["Date"].notna().any() else datetime.today().date()
            start_date, end_date = st.date_input("Select Date Range", value=[min_dt, max_dt], key="pf_daterange")
        filtered = df.copy()
        if name_filter:
            filtered = filtered[filtered["Patient Name"].str.contains(name_filter, case=False, na=False)]
        # apply date range
        filtered = filtered[
            (filtered["Date"] >= start_date) &
            (filtered["Date"] <= end_date)
        ]
        return filtered

    payments_filtered = payments_filter_ui(df_payments)

    # Display filtered payments with edit/delete controls
    if payments_filtered.empty:
        st.info("No payment records for the selected filters.")
    else:
        st.subheader("📋 Payments (filtered)")
        # iterate in ascending index order
        for idx, row in payments_filtered.sort_index().iterrows():
            sheet_row = idx + 2  # sheet rows start at 1, header at row 1 -> record 0 = sheet row 2
            title = f"{row['Patient Name']} — ₱{row['Amount Paid']:,.2f} — {row['Date']}"
            with st.expander(title):
                # Use unique keys so Streamlit keeps each input separate
                n_key = f"p_name_{idx}"
                a_key = f"p_amt_{idx}"
                d_key = f"p_date_{idx}"
                notes_key = f"p_notes_{idx}"

                new_name = st.text_input("Patient Name", value=row["Patient Name"], key=n_key)
                new_amount = st.number_input("Amount Paid", value=float(row["Amount Paid"]), min_value=0.0, step=0.01, format="%.2f", key=a_key)
                new_date = st.date_input("Date", value=row["Date"] if isinstance(row["Date"], date) else datetime.today().date(), key=d_key)
                new_notes = st.text_area("Notes", value=row["Notes"], key=notes_key)

                c1, c2 = st.columns([1,1])
                with c1:
                    if st.button("💾 Save Changes", key=f"save_pay_{idx}"):
                        update_row(ws_payments, sheet_row, [new_name, float(new_amount), new_date.isoformat(), new_notes])
                        st.success("Payment row updated.")
                        st.experimental_rerun()
                with c2:
                    if st.button("🗑️ Delete Row", key=f"del_pay_{idx}"):
                        delete_row(ws_payments, sheet_row)
                        st.warning("Payment row deleted.")
                        st.experimental_rerun()

    total_payments = df_payments["Amount Paid"].sum() if not df_payments.empty else 0.0
    filtered_total_payments = payments_filtered["Amount Paid"].sum() if not payments_filtered.empty else 0.0
    st.write(f"**Total Payments (all): ₱{total_payments:,.2f} — Filtered Total: ₱{filtered_total_payments:,.2f}**")

    # Download filtered payments CSV
    if not payments_filtered.empty:
        csv_pay = payments_filtered.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Filtered Payments CSV", csv_pay, "filtered_payments.csv", "text/csv", key="dl_pay")

    st.markdown("---")

    # ---------- EXPENSES SECTION ----------
    st.header("💸 Clinic Expenses")

    def expenses_filter_ui(df):
        if df.empty:
            st.info("No expenses yet.")
            return df
        with st.expander("🔎 Filters (Expenses)"):
            name_filter = st.text_input("Filter by Expense Name", key="ef_name")
            min_dt = df["Date"].min() if df["Date"].notna().any() else datetime.today().date()
            max_dt = df["Date"].max() if df["Date"].notna().any() else datetime.today().date()
            start_date, end_date = st.date_input("Select Date Range", value=[min_dt, max_dt], key="ef_daterange")
        filtered = df.copy()
        if name_filter:
            filtered = filtered[filtered["Expense Name"].str.contains(name_filter, case=False, na=False)]
        filtered = filtered[
            (filtered["Date"] >= start_date) &
            (filtered["Date"] <= end_date)
        ]
        return filtered

    expenses_filtered = expenses_filter_ui(df_expenses)

    if expenses_filtered.empty:
        st.info("No expense records for the selected filters.")
    else:
        st.subheader("📋 Expenses (filtered)")
        for idx, row in expenses_filtered.sort_index().iterrows():
            sheet_row = idx + 2
            title = f"{row['Expense Name']} — ₱{row['Amount']:,.2f} — {row['Date']}"
            with st.expander(title):
                n_key = f"e_name_{idx}"
                a_key = f"e_amt_{idx}"
                d_key = f"e_date_{idx}"
                notes_key = f"e_notes_{idx}"

                new_name = st.text_input("Expense Name", value=row["Expense Name"], key=n_key)
                new_amount = st.number_input("Amount", value=float(row["Amount"]), min_value=0.0, step=0.01, format="%.2f", key=a_key)
                new_date = st.date_input("Date", value=row["Date"] if isinstance(row["Date"], date) else datetime.today().date(), key=d_key)
                new_notes = st.text_area("Notes", value=row["Notes"], key=notes_key)

                c1, c2 = st.columns([1,1])
                with c1:
                    if st.button("💾 Save Changes", key=f"save_exp_{idx}"):
                        update_row(ws_expenses, sheet_row, [new_name, float(new_amount), new_date.isoformat(), new_notes])
                        st.success("Expense row updated.")
                        st.experimental_rerun()
                with c2:
                    if st.button("🗑️ Delete Row", key=f"del_exp_{idx}"):
                        delete_row(ws_expenses, sheet_row)
                        st.warning("Expense row deleted.")
                        st.experimental_rerun()

    total_expenses = df_expenses["Amount"].sum() if not df_expenses.empty else 0.0
    filtered_total_expenses = expenses_filtered["Amount"].sum() if not expenses_filtered.empty else 0.0
    st.write(f"**Total Expenses (all): ₱{total_expenses:,.2f} — Filtered Total: ₱{filtered_total_expenses:,.2f}**")

    if not expenses_filtered.empty:
        csv_exp = expenses_filtered.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Filtered Expenses CSV", csv_exp, "filtered_expenses.csv", "text/csv", key="dl_exp")

    st.markdown("---")

    # ---------- SUMMARY ----------
    st.header("📊 Summary")
    st.metric("Total Payments (all)", f"₱{total_payments:,.2f}")
    st.metric("Total Expenses (all)", f"₱{total_expenses:,.2f}")
    st.metric("Net Income", f"₱{(total_payments - total_expenses):,.2f}")

    # Logout button
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

# Run login or main
if not st.session_state.logged_in:
    login_screen()
else:
    main_app()
