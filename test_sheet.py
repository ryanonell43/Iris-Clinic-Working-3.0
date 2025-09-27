import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- APP TITLE ---
st.set_page_config(page_title="Clinic Payments & Expenses Tracker", layout="wide")
st.title("🏥 Clinic Payments & Expenses Tracker")

# --- GOOGLE SHEETS CONFIG ---
PAYMENTS_SHEET = "PatientPayments"
EXPENSES_SHEET = "ClinicExpenses"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Load credentials from Streamlit secrets
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)

# Open Sheets
payments_ws = client.open(PAYMENTS_SHEET).sheet1
expenses_ws = client.open(EXPENSES_SHEET).sheet1


# --- FUNCTIONS ---
def load_data(ws):
    """Load all records from the sheet into a DataFrame."""
    data = ws.get_all_records()
    return pd.DataFrame(data)


def add_row(ws, row_data):
    """Append a new row to the sheet."""
    ws.append_row(row_data)


def update_row(ws, row_index, row_data):
    """Update a specific row in the sheet (1-based index, incl. header)."""
    ws.update(f"A{row_index}:D{row_index}", [row_data])


def delete_row(ws, row_index):
    """Delete a row from the sheet (1-based index, incl. header)."""
    ws.delete_rows(row_index)


# --- NAVIGATION ---
menu = st.sidebar.radio("📌 Navigate", ["Add Payment", "Add Expense", "View Records"])

# --- ADD PAYMENT ---
if menu == "Add Payment":
    st.header("➕ Add New Patient Payment")

    with st.form("payment_form", clear_on_submit=True):
        patient_name = st.text_input("Patient Name")
        amount = st.number_input("Amount Paid", min_value=0.0, step=0.01)
        date = st.date_input("Date", value=datetime.today())
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add Payment")

        if submitted:
            add_row(payments_ws, [patient_name, amount, str(date), notes])
            st.success(f"✅ Payment added for {patient_name}")

# --- ADD EXPENSE ---
elif menu == "Add Expense":
    st.header("➕ Add New Clinic Expense")

    with st.form("expense_form", clear_on_submit=True):
        item = st.text_input("Expense Item")
        cost = st.number_input("Cost", min_value=0.0, step=0.01)
        date = st.date_input("Date", value=datetime.today())
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add Expense")

        if submitted:
            add_row(expenses_ws, [item, cost, str(date), notes])
            st.success(f"✅ Expense added: {item}")

# --- VIEW RECORDS ---
elif menu == "View Records":
    st.header("📊 View & Manage Records")

    tab1, tab2 = st.tabs(["💰 Payments", "📉 Expenses"])

    # ---- PAYMENTS TAB ----
    with tab1:
        df = load_data(payments_ws)

        if not df.empty:
            # Date filter
            st.subheader("Filter Payments by Date")
            min_date = pd.to_datetime(df["Date"]).min()
            max_date = pd.to_datetime(df["Date"]).max()
            start_date, end_date = st.date_input(
                "Select Date Range", [min_date, max_date]
            )

            df["Date"] = pd.to_datetime(df["Date"])
            mask = (df["Date"] >= pd.to_datetime(start_date)) & (
                df["Date"] <= pd.to_datetime(end_date)
            )
            filtered_df = df.loc[mask]

            st.dataframe(filtered_df)

            # Edit/Delete options
            st.subheader("Edit or Delete a Payment")
            if not filtered_df.empty:
                idx = st.number_input(
                    "Enter Row Number to Edit/Delete (first row = 2)", min_value=2, step=1
                )

                action = st.radio("Action", ["Edit", "Delete"])
                if action == "Edit":
                    row = df.iloc[idx - 2]  # adjust for header
                    with st.form("edit_payment"):
                        patient_name = st.text_input("Patient Name", row["Patient Name"])
                        amount = st.number_input("Amount Paid", value=float(row["Amount"]))
                        date = st.date_input("Date", value=row["Date"])
                        notes = st.text_area("Notes", row["Notes"])
                        save = st.form_submit_button("Save Changes")
                        if save:
                            update_row(
                                payments_ws,
                                idx,
                                [patient_name, amount, str(date), notes],
                            )
                            st.success("✅ Payment updated")
                            st.rerun()
                else:
                    if st.button("Delete Payment"):
                        delete_row(payments_ws, idx)
                        st.success("🗑️ Payment deleted")
                        st.rerun()
        else:
            st.info("No payments found.")

    # ---- EXPENSES TAB ----
    with tab2:
        df = load_data(expenses_ws)

        if not df.empty:
            # Date filter
            st.subheader("Filter Expenses by Date")
            min_date = pd.to_datetime(df["Date"]).min()
            max_date = pd.to_datetime(df["Date"]).max()
            start_date, end_date = st.date_input(
                "Select Date Range", [min_date, max_date], key="expense_dates"
            )

            df["Date"] = pd.to_datetime(df["Date"])
            mask = (df["Date"] >= pd.to_datetime(start_date)) & (
                df["Date"] <= pd.to_datetime(end_date)
            )
            filtered_df = df.loc[mask]

            st.dataframe(filtered_df)

            # Edit/Delete options
            st.subheader("Edit or Delete an Expense")
            if not filtered_df.empty:
                idx = st.number_input(
                    "Enter Row Number to Edit/Delete (first row = 2)",
                    min_value=2,
                    step=1,
                    key="expense_idx",
                )

                action = st.radio(
                    "Action", ["Edit", "Delete"], key="expense_action"
                )
                if action == "Edit":
                    row = df.iloc[idx - 2]  # adjust for header
                    with st.form("edit_expense"):
                        item = st.text_input("Expense Item", row["Expense Item"])
                        cost = st.number_input("Cost", value=float(row["Cost"]))
                        date = st.date_input("Date", value=row["Date"])
                        notes = st.text_area("Notes", row["Notes"])
                        save = st.form_submit_button("Save Changes")
                        if save:
                            update_row(
                                expenses_ws,
                                idx,
                                [item, cost, str(date), notes],
                            )
                            st.success("✅ Expense updated")
                            st.rerun()
                else:
                    if st.button("Delete Expense"):
                        delete_row(expenses_ws, idx)
                        st.success("🗑️ Expense deleted")
                        st.rerun()
        else:
            st.info("No expenses found.")
