import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- GOOGLE SHEETS CONFIG ---
SHEET_NAME = "PatientPayments"

# Authenticate with Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

st.title("💰 Patient Payments Tracker")

# --- Load existing data ---
def load_data():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

df = load_data()

# --- Display data ---
st.subheader("📊 Current Records")
if not df.empty:
    st.dataframe(df)
else:
    st.info("No records yet. Add one below.")

# --- Add new record ---
st.subheader("➕ Add New Payment")
with st.form("new_record"):
    patient_name = st.text_input("Patient Name")
    amount = st.number_input("Amount", min_value=0.0, step=0.01)
    date_paid = st.date_input("Date Paid", value=datetime.today())
    submit_new = st.form_submit_button("Add Payment")

if submit_new:
    new_data = [patient_name, amount, str(date_paid)]
    sheet.append_row(new_data)
    st.success("✅ Record added successfully!")
    st.rerun()

# --- Edit/Delete Existing Record ---
st.subheader("✏️ Edit or ❌ Delete a Record")

if not df.empty:
    # Let user select which row to edit
    row_to_edit = st.number_input("Enter row number to edit/delete (starting from 2)", min_value=2, max_value=len(df)+1, step=1)

    if st.button("Load Record"):
        row_data = sheet.row_values(row_to_edit)
        if row_data:
            st.write("📌 Selected Record:", row_data)

            # Pre-fill form for editing
            with st.form("edit_record"):
                patient_name_edit = st.text_input("Patient Name", value=row_data[0])
                amount_edit = st.number_input("Amount", min_value=0.0, step=0.01, value=float(row_data[1]))
                date_edit = st.date_input("Date Paid", value=datetime.strptime(row_data[2], "%Y-%m-%d").date())

                update_btn = st.form_submit_button("Update Record")

            if update_btn:
                sheet.update(f"A{row_to_edit}:C{row_to_edit}", [[patient_name_edit, amount_edit, str(date_edit)]])
                st.success("✅ Record updated successfully!")
                st.rerun()

            # Delete option
            if st.button("Delete Record"):
                sheet.delete_rows(row_to_edit)
                st.success("🗑️ Record deleted successfully!")
                st.rerun()
        else:
            st.error("Row not found. Please check the row number.")
else:
    st.info("No records available to edit or delete.")
