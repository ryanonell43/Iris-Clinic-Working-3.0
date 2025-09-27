import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- GOOGLE SHEETS CONFIG ---
SHEET_NAME = "PatientPayments"
EXPENSE_SHEET = "ClinicExpenses"

scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

# Load credentials from Streamlit secrets
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

# Open sheets
try:
    ws_patients = client.open(SHEET_NAME).sheet1
except:
    sh = client.create(SHEET_NAME)
    ws_patients = sh.sheet1
    ws_patients.append_row(["Patient Name", "Amount Paid", "Date", "Notes"])

try:
    ws_expenses = client.open(EXPENSE_SHEET).sheet1
except:
    sh = client.create(EXPENSE_SHEET)
    ws_expenses = sh.sheet1
    ws_expenses.append_row(["Expense Name", "Amount", "Date", "Notes"])

# --- HELPER FUNCTIONS ---
def load_data(worksheet):
    data = worksheet.get_all_records()
    return pd.DataFrame(data)


def save_data(worksheet, df):
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())


def crud_section(df, worksheet, label, cols):
    st.subheader(f"➕ Add New {label}")
    with st.form(f"add_{label.lower()}"):
        name = st.text_input(f"{label} Name")
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        date = st.date_input("Date", datetime.today())
        notes = st.text_area("Notes")
        submitted = st.form_submit_button(f"Add {label}")

        if submitted and name and amount:
            new_row = {cols[0]: name, cols[1]: amount, cols[2]: str(date), cols[3]: notes}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(worksheet, df)
            st.success(f"{label} added successfully!")

    # Display table with edit/delete options
    st.subheader(f"📋 Existing {label}s")
    if not df.empty:
        for i, row in df.iterrows():
            with st.expander(f"{row[cols[0]]} - ₱{row[cols[1]]:,.2f} on {row[cols[2]]}"):
                edit_name = st.text_input(f"Edit {label} Name", value=row[cols[0]], key=f"name_{label}_{i}")
                edit_amount = st.number_input("Edit Amount", value=float(row[cols[1]]), key=f"amount_{label}_{i}")
                edit_date = st.date_input("Edit Date", value=pd.to_datetime(row[cols[2]]).date(), key=f"date_{label}_{i}")
                edit_notes = st.text_area("Edit Notes", value=row[cols[3]], key=f"notes_{label}_{i}")

                if st.button("💾 Save Changes", key=f"save_{label}_{i}"):
                    df.at[i, cols[0]] = edit_name
                    df.at[i, cols[1]] = edit_amount
                    df.at[i, cols[2]] = str(edit_date)
                    df.at[i, cols[3]] = edit_notes
                    save_data(worksheet, df)
                    st.success(f"{label} updated successfully!")
                    st.experimental_rerun()

                if st.button("🗑️ Delete", key=f"delete_{label}_{i}"):
                    df = df.drop(i).reset_index(drop=True)
                    save_data(worksheet, df)
                    st.warning(f"{label} deleted successfully!")
                    st.experimental_rerun()

    total = df[cols[1]].sum() if not df.empty else 0
    st.write(f"**Total {label}s: ₱{total:,.2f}**")
    return df, total


def filter_dataframe(df, cols):
    if df.empty:
        return df

    with st.expander(f"🔎 Filter {cols[0]}s"):
        name_filter = st.text_input(f"Filter by {cols[0]} Name")

        # Default date range
        df[cols[2]] = pd.to_datetime(df[cols[2]], errors="coerce")
        min_date = df[cols[2]].min().date() if not df[cols[2]].isnull().all() else datetime.today().date()
        max_date = df[cols[2]].max().date() if not df[cols[2]].isnull().all() else datetime.today().date()

        start_date, end_date = st.date_input(
            "Select Date Range",
            value=[min_date, max_date]
        )

    filtered_df = df.copy()

    # Name filter
    if name_filter:
        filtered_df = filtered_df[filtered_df[cols[0]].str.contains(name_filter, case=False, na=False)]

    # Date range filter
    filtered_df = filtered_df[
        (filtered_df[cols[2]] >= pd.to_datetime(start_date)) &
        (filtered_df[cols[2]] <= pd.to_datetime(end_date))
    ]

    return filtered_df


# --- MAIN APP ---
def main_app():
    st.title("🏥 Clinic Finance Tracker")

    # Load data
    df_patients = load_data(ws_patients)
    df_expenses = load_data(ws_expenses)

    # Patient Payments Section
    st.header("💳 Patient Payments")
    df_patients, total_patients = crud_section(df_patients, ws_patients, "Payment",
