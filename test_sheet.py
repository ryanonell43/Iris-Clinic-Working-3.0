import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

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


def main_app():
    st.title("Patient Payments Tracker")

    # --- GOOGLE SHEETS CONFIG ---
    SHEET_NAME = "PatientPayments"
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        creds = Credentials.from_service_account_info(
            st.secrets["google_service_account"], scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet_connected = True
    except Exception as e:
        st.warning(f"Google Sheets not connected: {e}")
        sheet_connected = False

    # --- OPEN OR CREATE SHEET ---
    if sheet_connected:
        try:
            sheet = client.open(SHEET_NAME).sheet1
        except gspread.SpreadsheetNotFound:
            st.info(f"Sheet '{SHEET_NAME}' not found. Creating a new one...")
            sheet = client.create(SHEET_NAME).sheet1
            sheet.append_row(["Patient Name", "Amount Paid", "Date", "Notes"])
            st.success(f"Sheet '{SHEET_NAME}' created successfully!")

        records = sheet.get_all_records()
        df = pd.DataFrame(records)
    else:
        df = pd.DataFrame(columns=["Patient Name", "Amount Paid", "Date", "Notes"])

    # --- CLEAN COLUMN NAMES SAFELY ---
    if not df.empty:
        df.columns = df.columns.astype(str).str.strip()
        df.columns = [col.title() for col in df.columns]
    else:
        df = pd.DataFrame(columns=["Patient Name", "Amount Paid", "Date", "Notes"])

    # --- FILTER DATA ---
    st.subheader("Filter Payments")
    with st.expander("Filter Options"):
        patient_filter = st.text_input("Filter by Patient Name")
        start_date = st.date_input("Start Date", value=datetime.today())
        end_date = st.date_input("End Date", value=datetime.today())

    filtered_df = df.copy()

    if patient_filter and "Patient Name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Patient Name"].str.contains(patient_filter, case=False, na=False)
        ]

    if "Date" in filtered_df.columns:
        filtered_df["Date"] = pd.to_datetime(filtered_df["Date"], errors="coerce")
        filtered_df = filtered_df[
            (filtered_df["Date"] >= pd.to_datetime(start_date))
            & (filtered_df["Date"] <= pd.to_datetime(end_date))
        ]

    # --- DISPLAY FILTERED DATA ---
    st.dataframe(filtered_df)

    # --- TOTAL AMOUNT ---
    total_amount = filtered_df["Amount Paid"].sum() if not filtered_df.empty else 0.0
    st.subheader(f"Total Amount Paid: ₱{total_amount:,.2f}")

    # --- ADD NEW ENTRY ---
    st.subheader("Add New Payment")
    with st.form(key="add_payment_form"):
        patient_name = st.text_input("Patient Name")
        amount_paid = st.number_input("Amount Paid", min_value=0.0, step=0.01)
        date_input = st.date_input("Date", value=datetime.today())
        notes = st.text_area("Notes (optional)")
        submit = st.form_submit_button("Add Payment")

    if submit:
        if patient_name.strip() == "":
            st.error("Patient Name cannot be empty.")
        else:
            new_row = {
                "Patient Name": patient_name,
                "Amount Paid": amount_paid,
                "Date": str(date_input),
                "Notes": notes,
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.success(f"Added payment for {patient_name} successfully!")

            if sheet_connected:
                try:
                    sheet.append_row([patient_name, amount_paid, str(date_input), notes])
                except Exception as e:
                    st.error(f"Could not save to Google Sheet: {e}")

    # --- EDIT / DELETE ENTRY ---
    st.subheader("Edit or Delete Payment")
    if not df.empty:
        if "selected_index" not in st.session_state:
            st.session_state.selected_index = 0

        selected_index = st.number_input(
            "Select Row Index to Edit/Delete (starts at 0)",
            min_value=0,
            max_value=len(df) - 1,
            step=1,
            key="selected_index_input",
        )

        if st.button("Load Selected Row"):
            st.session_state.patient_name_val = df.at[selected_index, "Patient Name"]
            st.session_state.amount_paid_val = df.at[selected_index, "Amount Paid"]
            st.session_state.date_val = pd.to_datetime(df.at[selected_index, "Date"])
            st.session_state.notes_val = df.at[selected_index, "Notes"]

        if "patient_name_val" in st.session_state:
            new_name = st.text_input(
                "Patient Name", value=st.session_state.patient_name_val, key="edit_name"
            )
            new_amount = st.number_input(
                "Amount Paid",
                min_value=0.0,
                step=0.01,
                value=float(st.session_state.amount_paid_val),
                key="edit_amount",
            )
            new_date = st.date_input(
                "Date", value=st.session_state.date_val, key="edit_date"
            )
            new_notes = st.text_area(
                "Notes", value=st.session_state.notes_val, key="edit_notes"
            )

            if st.button("Update Row"):
                df.at[selected_index, "Patient Name"] = new_name
                df.at[selected_index, "Amount Paid"] = new_amount
                df.at[selected_index, "Date"] = str(new_date)
                df.at[selected_index, "Notes"] = new_notes

                if sheet_connected:
                    try:
                        sheet.update(
                            f"A{selected_index + 2}:D{selected_index + 2}",
                            [[new_name, new_amount, str(new_date), new_notes]],
                        )
                    except Exception as e:
                        st.error(f"Could not update Google Sheet: {e}")

                st.success("Row updated successfully!")

            if st.button("Delete Row"):
                df = df.drop(selected_index).reset_index(drop=True)

                if sheet_connected:
                    try:
                        sheet.delete_rows(selected_index + 2)
                    except Exception as e:
                        st.error(f"Could not delete from Google Sheet: {e}")

                st.success("Row deleted successfully!")

                for key in [
                    "patient_name_val",
                    "amount_paid_val",
                    "date_val",
                    "notes_val",
                ]:
                    if key in st.session_state:
                        del st.session_state[key]

    # --- DOWNLOAD CSV ---
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="patient_payments.csv",
        mime="text/csv",
    )

    # --- LOGOUT BUTTON ---
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()


# --- RUN APP ---
if not st.session_state.logged_in:
    login_screen()
else:
    main_app()
