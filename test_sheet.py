import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import json

# --- LOGIN SETUP ---
USERNAME = "irisclinic"
PASSWORD = "welcome01"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_screen():
    st.title("🔐 Login to Iris Clinic App")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == USERNAME and password == PASSWORD:
            st.session_state.logged_in = True
            st.success("✅ Login successful! Redirecting...")
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

def connect_google_sheets(sheet_name):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        creds_dict = json.loads(st.secrets["google_service_account"]["json"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name)
        return sheet
    except Exception as e:
        st.warning(f"Google Sheets not connected: {e}")
        return None

def load_or_create_worksheet(sheet, worksheet_name, headers):
    try:
        ws = sheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=worksheet_name, rows="1000", cols=len(headers))
        ws.append_row(headers)
        st.success(f"Worksheet '{worksheet_name}' created!")
    return ws

def filter_dataframe(df, cols, section_name):
    if df.empty:
        return df

    with st.expander(f"🔎 Filter {section_name}"):
        name_filter = st.text_input(f"Filter by {cols[0]}")
        start_date = st.date_input("Start Date", value=datetime.today())
        end_date = st.date_input("End Date", value=datetime.today())

    filtered_df = df.copy()

    if name_filter:
        filtered_df = filtered_df[filtered_df[cols[0]].str.contains(name_filter, case=False, na=False)]

    if cols[2] in filtered_df.columns:
        filtered_df[cols[2]] = pd.to_datetime(filtered_df[cols[2]], errors="coerce")
        filtered_df = filtered_df[
            (filtered_df[cols[2]] >= pd.to_datetime(start_date)) &
            (filtered_df[cols[2]] <= pd.to_datetime(end_date))
        ]

    return filtered_df

def crud_section(df, ws, section_name, cols):
    st.subheader(f"{section_name} List")
    st.dataframe(df)

    total = df[cols[1]].sum() if not df.empty else 0.0
    st.write(f"**Total {section_name}: ₱{total:,.2f}**")

    # --- ADD NEW ---
    with st.form(f"add_{section_name.lower()}"):
        name = st.text_input(f"{cols[0]}")
        amt = st.number_input("Amount", min_value=0.0, step=0.01, key=f"amt_{section_name}")
        date = st.date_input("Date", value=datetime.today(), key=f"date_{section_name}")
        notes = st.text_area("Notes", key=f"notes_{section_name}")
        submit = st.form_submit_button(f"Add {section_name}")

    if submit and name.strip() != "":
        new_row = [name, amt, str(date), notes]
        df.loc[len(df)] = new_row
        if ws:
            ws.append_row(new_row)
        st.success(f"✅ {section_name} added!")

    # --- EDIT/DELETE ---
    if not df.empty:
        idx = st.number_input(
            f"Select Row Index to Edit/Delete ({section_name})", 
            min_value=0, max_value=len(df)-1, step=1, key=f"idx_{section_name}"
        )

        if st.button(f"Load {section_name} Row", key=f"load_{section_name}"):
            st.session_state[f"{section_name}_vals"] = {
                "name": df.at[idx, cols[0]],
                "amt": float(df.at[idx, cols[1]]),
                "date": pd.to_datetime(df.at[idx, cols[2]]),
                "notes": df.at[idx, cols[3]]
            }

        if f"{section_name}_vals" in st.session_state:
            vals = st.session_state[f"{section_name}_vals"]

            new_name = st.text_input(cols[0], value=vals["name"], key=f"edit_name_{section_name}")
            new_amt = st.number_input("Amount", min_value=0.0, step=0.01, value=vals["amt"], key=f"edit_amt_{section_name}")
            new_date = st.date_input("Date", value=vals["date"], key=f"edit_date_{section_name}")
            new_notes = st.text_area("Notes", value=vals["notes"], key=f"edit_notes_{section_name}")

            if st.button("Update Row", key=f"update_{section_name}"):
                df.at[idx, cols[0]] = new_name
                df.at[idx, cols[1]] = new_amt
                df.at[idx, cols[2]] = str(new_date)
                df.at[idx, cols[3]] = new_notes

                if ws:
                    ws.update(
                        f"A{idx+2}:D{idx+2}",
                        [[new_name, new_amt, str(new_date), new_notes]]
                    )
                st.success(f"{section_name} row updated!")

            if st.button("Delete Row", key=f"delete_{section_name}"):
                df = df.drop(idx).reset_index(drop=True)
                if ws:
                    ws.delete_rows(idx+2)
                st.success(f"{section_name} row deleted!")

                del st.session_state[f"{section_name}_vals"]

    return df, total

def main_app():
    st.title("Clinic Finance Tracker")

    SHEET_NAME = "PatientPayments"
    sheet = connect_google_sheets(SHEET_NAME)

    # Patients Worksheet
    if sheet:
        ws_patients = load_or_create_worksheet(sheet, "Payments", ["Patient Name", "Amount Paid", "Date", "Notes"])
        df_patients = pd.DataFrame(ws_patients.get_all_records())
    else:
        ws_patients = None
        df_patients = pd.DataFrame(columns=["Patient Name", "Amount Paid", "Date", "Notes"])

    if df_patients.empty:
        df_patients = pd.DataFrame(columns=["Patient Name", "Amount Paid", "Date", "Notes"])

    # Expenses Worksheet
    if sheet:
        ws_expenses = load_or_create_worksheet(sheet, "Expenses", ["Expense Name", "Amount", "Date", "Notes"])
        df_expenses = pd.DataFrame(ws_expenses.get_all_records())
    else:
        ws_expenses = None
        df_expenses = pd.DataFrame(columns=["Expense Name", "Amount", "Date", "Notes"])

    if df_expenses.empty:
        df_expenses = pd.DataFrame(columns=["Expense Name", "Amount", "Date", "Notes"])

    # Payments Section
    st.header("💳 Patient Payments")
    df_patients, total_patients = crud_section(df_patients, ws_patients, "Payment", ["Patient Name", "Amount Paid", "Date", "Notes"])
    df_patients_filtered = filter_dataframe(df_patients, ["Patient Name", "Amount Paid", "Date", "Notes"], "Payments")
    st.subheader("📋 Filtered Payments")
    st.dataframe(df_patients_filtered)
    st.write(f"**Filtered Total Payments: ₱{df_patients_filtered['Amount Paid'].sum():,.2f}**")

    # Expenses Section
    st.header("💸 Clinic Expenses")
    df_expenses, total_expenses = crud_section(df_expenses, ws_expenses, "Expense", ["Expense Name", "Amount", "Date", "Notes"])
    df_expenses_filtered = filter_dataframe(df_expenses, ["Expense Name", "Amount", "Date", "Notes"], "Expenses")
    st.subheader("📋 Filtered Expenses")
    st.dataframe(df_expenses_filtered)
    st.write(f"**Filtered Total Expenses: ₱{df_expenses_filtered['Amount'].sum():,.2f}**")

    # Summary
    st.header("📊 Summary")
    st.write(f"**Total Payments: ₱{total_patients:,.2f}**")
    st.write(f"**Total Expenses: ₱{total_expenses:,.2f}**")
    st.write(f"**Net Income: ₱{total_patients-total_expenses:,.2f}**")

    # Downloads
    st.download_button("Download Payments CSV", df_patients.to_csv(index=False).encode("utf-8"),
                       "patient_payments.csv", "text/csv")
    st.download_button("Download Expenses CSV", df_expenses.to_csv(index=False).encode("utf-8"),
                       "clinic_expenses.csv", "text/csv")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- RUN APP ---
if not st.session_state.logged_in:
    login_screen()
else:
    main_app()
