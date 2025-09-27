import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- APP TITLE ---
st.title("Patient Payments Tracker")

# --- GOOGLE SHEETS CONFIG ---
SHEET_NAME = "PatientPayments"

# Define the scope
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials from secrets
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)

# Authorize client
client = gspread.authorize(creds)

# Open existing Google Sheet (make sure you shared it with your service account)
sh = client.open(SHEET_NAME)
worksheet = sh.sheet1

# --- FUNCTIONS ---
def load_data():
    """Load all payment records from the sheet into a DataFrame."""
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def add_payment(patient_name, amount, date, notes):
    """Append a new payment record to the sheet."""
    worksheet.append_row([patient_name, amount, date, notes])

# --- INPUT FORM ---
st.header("Add New Payment")

with st.form("payment_form", clear_on_submit=True):
    patient_name = st.text_input("Patient Name")
    amount = st.number_input("Amount Paid", min_value=0.0, step=0.01)
    date = st.date_input("Date", value=datetime.today())
    notes = st.text_area("Notes")
    submitted = st.form_submit_button("Add Payment")

    if submitted:
        add_payment(patient_name, amount, str(date), notes)
        st.success(f"✅ Added payment for {patient_name}")

# --- DISPLAY DATA ---
st.header("Payment Records")

df = load_data()

if not df.empty:
    st.dataframe(df)

    # --- DOWNLOAD OPTION ---
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download CSV",
        csv,
        "patient_payments.csv",
        "text/csv",
        key="download-csv"
    )
else:
    st.info("No payment records found yet.")
