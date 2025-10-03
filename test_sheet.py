import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import json

st.set_page_config(page_title="Patient Payments Tracker", layout="wide")
st.title("💳 Patient Payments Tracker")

# --- GOOGLE SHEETS CONFIG ---
SHEET_NAME = "PatientPayments"

# Load credentials
with open("secrets.json") as f:
    creds_data = json.load(f)

creds = Credentials.from_service_account_info(
    creds_data,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

client = gspread.authorize(creds)
sh = client.open(SHEET_NAME)

def load_data():
    worksheet = sh.sheet1
    data = worksheet.get_all_records()
    return pd.DataFrame(data), worksheet

def add_row(patient, date, amount, notes):
    worksheet = sh.sheet1
    worksheet.append_row([patient, date, amount, notes])

def update_row(row_number, patient, date, amount, notes):
    worksheet = sh.sheet1
    worksheet.update(f"A{row_number}:D{row_number}", [[patient, date, amount, notes]])

def delete_row(row_number):
    worksheet = sh.sheet1
    worksheet.delete_rows(row_number)

# --- LOAD DATA ---
df, worksheet = load_data()

# --- ADD ENTRY ---
st.subheader("➕ Add Payment Entry")
with st.form("add_form", clear_on_submit=True):
    patient = st.text_input("Patient Name")
    date = st.date_input("Date", datetime.today())
    amount = st.number_input("Amount", min_value=0.0, step=0.01)
    notes = st.text_input("Notes (optional)")
    submitted = st.form_submit_button("Add Entry")
    if submitted and patient and amount > 0:
        add_row(patient, str(date), amount, notes)
        st.success("✅ Payment entry added!")

# --- EDIT ENTRY ---
st.subheader("✏️ Edit Payment Entry")
with st.form("edit_form"):
    row_to_edit = st.number_input("Row number to edit", min_value=2, step=1)  # skip headers
    new_patient = st.text_input("New Patient Name")
    new_date = st.date_input("New Date", datetime.today())
    new_amount = st.number_input("New Amount", min_value=0.0, step=0.01)
    new_notes = st.text_input("New Notes")
    edit_submitted = st.form_submit_button("Update Row")
    if edit_submitted and row_to_edit:
        update_row(row_to_edit, new_patient, str(new_date), new_amount, new_notes)
        st.success(f"✅ Row {row_to_edit} updated!")

# --- DELETE ENTRY ---
st.subheader("🗑️ Delete Payment Entry")
with st.form("delete_form"):
    row_to_delete = st.number_input("Row number to delete", min_value=2, step=1)  # skip headers
    delete_submitted = st.form_submit_button("Delete Row")
    if delete_submitted and row_to_delete:
        delete_row(row_to_delete)
        st.warning(f"❌ Row {row_to_delete} deleted!")

# --- FILTER + VIEW DATA ---
st.subheader("📊 Payment Records")

with st.expander("🔎 Filter Data"):
    patient_filter = st.text_input("Search by Patient Name")
    date_filter = st.date_input("Filter by Date", None)

filtered_df = df.copy()

# Filter by patient
if patient_filter:
    filtered_df = filtered_df[filtered_df["Patient"].str.contains(patient_filter, case=False, na=False)]

# Filter by date
if date_filter:
    filtered_df = filtered_df[filtered_df["Date"] == str(date_filter)]

st.dataframe(filtered_df)

# --- TOTALS ---
if "Amount" in filtered_df.columns:
    total_payments = filtered_df["Amount"].sum()
    st.metric("💰 Total Payments", f"₱{total_payments:,.2f}")
