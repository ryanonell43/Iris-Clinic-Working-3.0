import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- GOOGLE SHEETS CONFIG ---
SHEET_NAME = "PatientPayments"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- CONNECT TO GOOGLE SHEETS ---
def connect_gsheet():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(credentials)
    return client.open(SHEET_NAME).sheet1

# --- LOAD DATA ---
def load_data(sheet):
    records = sheet.get_all_records()
    return pd.DataFrame(records)

# --- ADD NEW ROW ---
def add_record(sheet, data):
    sheet.append_row(data)

# --- UPDATE ROW (by row number) ---
def update_row(sheet, row_number, data):
    sheet.update(f"A{row_number}:D{row_number}", [data])

# --- DELETE ROW (by row number) ---
def delete_row(sheet, row_number):
    sheet.delete_rows(row_number)

# --- MAIN APP ---
def main():
    st.title("Patient Payments Tracker")

    sheet = connect_gsheet()
    df = load_data(sheet)

    if not df.empty:
        st.subheader("📋 Patient Records")
        st.dataframe(df)

    # Add record
    st.subheader("➕ Add New Record")
    with st.form("add_form"):
        patient_name = st.text_input("Patient Name")
        service = st.text_input("Service")
        amount_paid = st.number_input("Amount Paid", min_value=0.0, step=0.01)
        date = st.date_input("Date", datetime.today())
        submitted = st.form_submit_button("Add Record")

        if submitted:
            data = [patient_name, service, amount_paid, str(date)]
            add_record(sheet, data)
            st.success("✅ Record added successfully!")
            st.experimental_rerun()  # Auto-refresh

    # Edit record
    st.subheader("✏️ Edit Record (by Row Number)")
    with st.form("edit_form"):
        row_number = st.number_input(
            "Row Number to Edit (starts at 2)", min_value=2, step=1
        )
        patient_name = st.text_input("New Patient Name")
        service = st.text_input("New Service")
        amount_paid = st.number_input(
            "New Amount Paid", min_value=0.0, step=0.01, key="edit_amount"
        )
        date = st.date_input("New Date", datetime.today(), key="edit_date")
        edit_submitted = st.form_submit_button("Update Record")

        if edit_submitted:
            data = [patient_name, service, amount_paid, str(date)]
            update_row(sheet, row_number, data)
            st.success(f"✅ Row {row_number} updated successfully!")
            st.experimental_rerun()  # Auto-refresh

    # Delete record
    st.subheader("🗑️ Delete Record (by Row Number)")
    with st.form("delete_form"):
        del_row_number = st.number_input(
            "Row Number to Delete (starts at 2)", min_value=2, step=1, key="delete"
        )
        del_submitted = st.form_submit_button("Delete Record")

        if del_submitted:
            delete_row(sheet, del_row_number)
            st.success(f"🗑️ Row {del_row_number} deleted successfully!")
            st.experimental_rerun()  # Auto-refresh


if __name__ == "__main__":
    main()
