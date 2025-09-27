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

# --- GOOGLE SHEETS CONNECTION ---
def connect_to_gsheets(sheet_name):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        creds_dict = json.loads(st.secrets["google_service_account"]["json"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        try:
            sheet = client.open(sheet_name).sheet1
        except gspread.SpreadsheetNotFound:
            st.warning(f"'{sheet_name}' not found. Please create it in Google Sheets and share it with the service account.")
            return None
        return sheet
    except Exception as e:
        st.error(f"Google Sheets connection failed: {e}")
        return None

def app_for_sheet(sheet, sheet_title):
    st.header(sheet_title)

    # --- LOAD DATA ---
    if sheet:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
    else:
        df = pd.DataFrame()

    # Ensure correct schema
    expected_cols = ["Name", "Amount", "Date", "Notes"]
    if df.empty:
        df = pd.DataFrame(columns=expected_cols)
    else:
        df.columns = [col.title().strip() for col in df.columns]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""

    # --- FILTER DATA ---
    st.subheader("🔍 Filter Records")
    with st.expander("Filter Options", expanded=True):
        name_filter = st.text_input("Filter by Name")
        if not df.empty and "Date" in df.columns:
            try:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                min_date = df["Date"].min().date()
                max_date = df["Date"].max().date()
            except Exception:
                min_date = max_date = datetime.today().date()
        else:
            min_date = max_date = datetime.today().date()

        start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

    filtered_df = df.copy()
    if name_filter:
        filtered_df = filtered_df[filtered_df["Name"].str.contains(name_filter, case=False, na=False)]
    if not filtered_df.empty and "Date" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Date"].dt.date >= start_date) &
            (filtered_df["Date"].dt.date <= end_date)
        ]

    st.dataframe(filtered_df)

    # --- TOTAL ---
    total_amount = filtered_df["Amount"].sum() if not filtered_df.empty else 0.0
    st.subheader(f"💰 Total Amount: ₱{total_amount:,.2f}")

    # --- ADD NEW ENTRY ---
    st.subheader("➕ Add New Record")
    with st.form(key=f"add_form_{sheet_title}"):
        name = st.text_input("Name")
        amount = st.number_input("Amount", min_value=0.0, step=0.01)
        date_input = st.date_input("Date", value=datetime.today())
        notes = st.text_area("Notes (optional)")
        submit = st.form_submit_button("Add")
        if submit:
            if name.strip() == "":
                st.error("Name cannot be empty.")
            else:
                new_row = {"Name": name, "Amount": amount, "Date": str(date_input), "Notes": notes}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                if sheet:
                    try:
                        sheet.append_row([name, amount, str(date_input), notes])
                        st.success(f"Added record for {name} successfully!")
                    except Exception as e:
                        st.error(f"Could not save to Google Sheet: {e}")

    # --- EDIT / DELETE ENTRY ---
    st.subheader("✏️ Edit or Delete Record")
    if not df.empty:
        selected_index = st.number_input(
            "Select Row Index (starts at 0)", min_value=0, max_value=len(df)-1, step=1
        )

        if st.button("Load Selected Row", key=f"load_{sheet_title}"):
            st.session_state[f"{sheet_title}_edit"] = {
                "Name": df.at[selected_index, "Name"],
                "Amount": df.at[selected_index, "Amount"],
                "Date": pd.to_datetime(df.at[selected_index, "Date"]),
                "Notes": df.at[selected_index, "Notes"],
                "Index": selected_index
            }

        if f"{sheet_title}_edit" in st.session_state:
            edit_data = st.session_state[f"{sheet_title}_edit"]
            new_name = st.text_input("Name", value=edit_data["Name"])
            new_amount = st.number_input("Amount", min_value=0.0, step=0.01, value=float(edit_data["Amount"]))
            new_date = st.date_input("Date", value=edit_data["Date"])
            new_notes = st.text_area("Notes", value=edit_data["Notes"])

            if st.button("Update Row", key=f"update_{sheet_title}"):
                df.at[edit_data["Index"], "Name"] = new_name
                df.at[edit_data["Index"], "Amount"] = new_amount
                df.at[edit_data["Index"], "Date"] = str(new_date)
                df.at[edit_data["Index"], "Notes"] = new_notes
                if sheet:
                    try:
                        sheet.update(
                            f"A{edit_data['Index']+2}:D{edit_data['Index']+2}",
                            [[new_name, new_amount, str(new_date), new_notes]]
                        )
                        st.success("Row updated successfully!")
                    except Exception as e:
                        st.error(f"Could not update Google Sheet: {e}")

            if st.button("Delete Row", key=f"delete_{sheet_title}"):
                df = df.drop(edit_data["Index"]).reset_index(drop=True)
                if sheet:
                    try:
                        sheet.delete_rows(edit_data["Index"]+2)
                        st.success("Row deleted successfully!")
                    except Exception as e:
                        st.error(f"Could not delete from Google Sheet: {e}")
                del st.session_state[f"{sheet_title}_edit"]

    # --- DOWNLOAD CSV ---
    st.download_button(
        label="📥 Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{sheet_title.lower().replace(' ','_')}.csv",
        mime="text/csv"
    )

def main_app():
    st.title("🏥 Iris Clinic Management App")

    menu = ["💳 Patient Payments", "💸 Expenses"]
    choice = st.sidebar.radio("Navigate", menu)

    if choice == "💳 Patient Payments":
        payments_sheet = connect_to_gsheets("PatientPayments")
        app_for_sheet(payments_sheet, "Patient Payments")
    elif choice == "💸 Expenses":
        expenses_sheet = connect_to_gsheets("Expenses")
        app_for_sheet(expenses_sheet, "Expenses")

    # --- LOGOUT BUTTON ---
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- RUN APP ---
if not st.session_state.logged_in:
    login_screen()
else:
    main_app()
