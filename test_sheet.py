import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- GOOGLE SHEETS CONFIG ---
SHEET_NAME = "PatientPayments"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Load credentials from secrets
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPES
)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

st.title("💰 Patient Payments Tracker")

# --- FUNCTIONS ---
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def add_row(date, patient, amount, notes):
    sheet.append_row([date, patient, amount, notes])

def update_row(row_index, date, patient, amount, notes):
    # row_index comes from pandas (0-based), add 2 to match Google Sheets (header + 1)
    sheet.update(
        f"A{row_index+2}:D{row_index+2}",
        [[date, patient, amount, notes]]
    )

def delete_row(row_index):
    sheet.delete_rows(row_index+2)

# --- MAIN APP ---
action = st.radio("Choose an action", ["Add Payment", "View Payments", "Edit/Delete Payment"])

if action == "Add Payment":
    st.subheader("➕ Add New Payment")

    date = st.date_input("Date", datetime.today()).strftime("%Y-%m-%d")
    patient = st.text_input("Patient Name")
    amount = st.number_input("Amount", min_value=0.0, step=0.01)
    notes = st.text_area("Notes")

    if st.button("Add Payment"):
        if patient.strip() == "":
            st.warning("⚠️ Please enter a patient name.")
        else:
            add_row(date, patient, amount, notes)
            st.success("✅ Payment added successfully!")

elif action == "View Payments":
    st.subheader("📋 All Payments")
    df = load_data()
    st.dataframe(df)

elif action == "Edit/Delete Payment":
    st.subheader("✏️ Edit or 🗑️ Delete Payment")
    df = load_data()

    if df.empty:
        st.warning("⚠️ No records available.")
    else:
        st.dataframe(df)

        # Select row
        row_index = st.number_input(
            "Enter Row Index to Edit/Delete (starting from 0)",
            min_value=0, max_value=len(df)-1, step=1
        )

        selected = df.iloc[row_index]
        st.write("Selected Row:", selected.to_dict())

        # Prefilled fields for editing
        date = st.text_input("Date", selected["Date"])
        patient = st.text_input("Patient", selected["Patient"])
        amount = st.number_input("Amount", value=float(selected["Amount"]), step=0.01)
        notes = st.text_area("Notes", selected["Notes"])

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Update Row"):
                update_row(row_index, date, patient, amount, notes)
                st.success(f"✅ Row {row_index} updated successfully!")

        with col2:
            if st.button("Delete Row"):
                delete_row(row_index)
                st.error(f"❌ Row {row_index} deleted successfully!")
