import streamlit as st
import gspread
import pandas as pd
import json
from datetime import datetime
from google.oauth2.service_account import Credentials

# -------------------
# CONFIG
# -------------------
PATIENT_SHEET = "PatientPayments"
EXPENSES_SHEET = "Expenses"

st.set_page_config(page_title="Clinic Tracker", layout="wide")

# -------------------
# AUTHENTICATION
# -------------------
def get_gspread_client():
    try:
        service_account_info = json.loads(st.secrets["google_service_account"]["json"])
        creds = Credentials.from_service_account_info(service_account_info, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheets not connected: {e}")
        return None

client = get_gspread_client()

if client:
    try:
        patient_ws = client.open(PATIENT_SHEET).sheet1
    except Exception:
        st.error(f"Could not open {PATIENT_SHEET} sheet. Please create it and share access.")
        st.stop()

    try:
        expenses_ws = client.open(EXPENSES_SHEET).sheet1
    except Exception:
        st.error(f"Could not open {EXPENSES_SHEET} sheet. Please create it and share access.")
        st.stop()
else:
    st.stop()

# -------------------
# HELPERS
# -------------------
def load_data(ws):
    data = ws.get_all_records()
    return pd.DataFrame(data)

def save_row(ws, row):
    ws.append_row(row)

def overwrite_data(ws, df):
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist())

# -------------------
# MAIN APP
# -------------------
st.title("🏥 Clinic Tracker")

tabs = st.tabs(["Patients", "Expenses"])

# -------------------
# PATIENTS TAB
# -------------------
with tabs[0]:
    st.header("Patient Payments")

    with st.form("patient_form"):
        name = st.text_input("Patient Name")
        amount = st.number_input("Amount Paid", min_value=0.0, step=0.01)
        date = st.date_input("Date", value=datetime.today())
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add Payment")

        if submitted:
            if name and amount > 0:
                save_row(patient_ws, [name, amount, str(date), notes])
                st.success("Payment added successfully!")
                st.rerun()
            else:
                st.error("Please fill in all required fields.")

    # Load and display
    df_patients = load_data(patient_ws)
    if not df_patients.empty:
        df_patients["Date"] = pd.to_datetime(df_patients["Date"], errors="coerce")
        start_date, end_date = st.date_input("Filter by date", [df_patients["Date"].min(), df_patients["Date"].max()])

        filtered = df_patients[(df_patients["Date"] >= pd.to_datetime(start_date)) &
                               (df_patients["Date"] <= pd.to_datetime(end_date))]

        st.dataframe(filtered)

        # Edit/Delete
        if not filtered.empty:
            row_to_edit = st.number_input("Row number to edit/delete", min_value=1, max_value=len(df_patients), step=1)
            action = st.radio("Action", ["Edit", "Delete"], horizontal=True)

            if st.button("Apply"):
                df = df_patients.copy()
                if action == "Delete":
                    df = df.drop(df.index[row_to_edit - 1])
                else:
                    edit_name = st.text_input("Edit Name", df.iloc[row_to_edit - 1]["Patient Name"])
                    edit_amount = st.number_input("Edit Amount", value=float(df.iloc[row_to_edit - 1]["Amount Paid"]))
                    edit_date = st.date_input("Edit Date", value=df.iloc[row_to_edit - 1]["Date"])
                    edit_notes = st.text_area("Edit Notes", df.iloc[row_to_edit - 1]["Notes"])
                    df.iloc[row_to_edit - 1] = [edit_name, edit_amount, str(edit_date), edit_notes]

                overwrite_data(patient_ws, df)
                st.success(f"Row {row_to_edit} updated successfully!")
                st.rerun()

# -------------------
# EXPENSES TAB
# -------------------
with tabs[1]:
    st.header("Expenses")

    with st.form("expense_form"):
        description = st.text_input("Expense Description")
        amount = st.number_input("Expense Amount", min_value=0.0, step=0.01)
        date = st.date_input("Date", value=datetime.today())
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add Expense")

        if submitted:
            if description and amount > 0:
                save_row(expenses_ws, [description, amount, str(date), notes])
                st.success("Expense added successfully!")
                st.rerun()
            else:
                st.error("Please fill in all required fields.")

    # Load and display
    df_expenses = load_data(expenses_ws)
    if not df_expenses.empty:
        df_expenses["Date"] = pd.to_datetime(df_expenses["Date"], errors="coerce")
        start_date, end_date = st.date_input("Filter by date", [df_expenses["Date"].min(), df_expenses["Date"].max()])

        filtered = df_expenses[(df_expenses["Date"] >= pd.to_datetime(start_date)) &
                               (df_expenses["Date"] <= pd.to_datetime(end_date))]

        st.dataframe(filtered)

        # Edit/Delete
        if not filtered.empty:
            row_to_edit = st.number_input("Row number to edit/delete", min_value=1, max_value=len(df_expenses), step=1)
            action = st.radio("Action", ["Edit", "Delete"], horizontal=True)

            if st.button("Apply", key="expenses_apply"):
                df = df_expenses.copy()
                if action == "Delete":
                    df = df.drop(df.index[row_to_edit - 1])
                else:
                    edit_desc = st.text_input("Edit Description", df.iloc[row_to_edit - 1]["Expense Description"])
                    edit_amount = st.number_input("Edit Amount", value=float(df.iloc[row_to_edit - 1]["Expense Amount"]))
                    edit_date = st.date_input("Edit Date", value=df.iloc[row_to_edit - 1]["Date"])
                    edit_notes = st.text_area("Edit Notes", df.iloc[row_to_edit - 1]["Notes"])
                    df.iloc[row_to_edit - 1] = [edit_desc, edit_amount, str(edit_date), edit_notes]

                overwrite_data(expenses_ws, df)
                st.success(f"Row {row_to_edit} updated successfully!")
                st.rerun()
