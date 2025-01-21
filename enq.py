import os
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import streamlit.components.v1 as components  # For embedding HTML/JS

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize Firebase
def init_firebase():
    try:
        if not firebase_admin._apps:
            firebase_cred = credentials.Certificate({
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/v1/certs",
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_EMAIL").replace(
                    "firebase-adminsdk", "metadata/x509/firebase-adminsdk"
                )
            })
            firebase_admin.initialize_app(firebase_cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Error initializing Firebase: {e}")
        st.stop()

# Initialize Google Sheets
def init_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        google_creds = {
            "type": "service_account",
            "project_id": os.getenv("GSPREAD_PROJECT_ID"),
            "private_key_id": os.getenv("GSPREAD_PRIVATE_KEY_ID"),
            "private_key": os.getenv("GSPREAD_PRIVATE_KEY").replace("\\n", "\n"),
            "client_email": os.getenv("GSPREAD_CLIENT_EMAIL"),
            "client_id": os.getenv("GSPREAD_CLIENT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/v1/certs",
            "client_x509_cert_url": os.getenv("GSPREAD_CLIENT_EMAIL").replace(
                "samarth-s-api", "metadata/x509/samarth-s-api"
            ),
        }
        client = gspread.service_account_from_dict(google_creds)
        sheet = client.open_by_key(os.getenv("GSPREAD_SHEET_ID")).sheet1

        # Initialize the sheet if empty
        if not sheet.get_all_records():
            sheet.append_row([
                "Enquiry ID", "Buyer Agent Number", "Property ID", "Seller Agent Number",
                "Seller Agent Name", "CP_ID", "Seller Agent KAM", "Date of Status Last Checked",
                "Added", "Last Modified", "Status"
            ])
        return sheet
    except Exception as e:
        st.error(f"Error initializing Google Sheets: {e}")
        st.stop()

# Save data to Google Sheet
def save_to_google_sheet(sheet, enquiry_data):
    try:
        sheet.append_row([
            enquiry_data.get("enquiryId", ""),
            enquiry_data.get("buyerAgentNumber", ""),
            enquiry_data.get("propertyId", ""),
            enquiry_data.get("sellerAgentNumber", ""),
            enquiry_data.get("sellerAgentName", ""),
            enquiry_data.get("cpId", ""),
            enquiry_data.get("sellerAgentKAM", ""),
            enquiry_data.get("dateOfStatusLastChecked", ""),
            enquiry_data.get("added", ""),
            enquiry_data.get("lastModified", ""),
            enquiry_data.get("status", "")
        ])
    except Exception as e:
        st.error(f"Error saving to Google Sheet: {e}")

# Fetch data from Firebase and save to Google Sheets
def fetch_data_and_save(db, sheet, property_id, buyer_agent_number):
    try:
        property_id = property_id.upper()

        # Fetch property details
        inventories_ref = db.collection("ACN123")
        inventory_query = inventories_ref.where("propertyId", "==", property_id).stream()
        property_details = next((doc.to_dict() for doc in inventory_query), None)

        if not property_details:
            st.error("No property found for the given Property ID.")
            return None

        # Convert Unix timestamp to date (if applicable)
        unix_timestamp = property_details.get("dateOfStatusLastChecked")
        if unix_timestamp:
            # Convert to date format
            date_of_status_last_checked = datetime.fromtimestamp(unix_timestamp).strftime('%Y-%m-%d')
        else:
            date_of_status_last_checked = "Unknown"

        # Fetch agent details
        cp_id = property_details.get("cpCode")
        agents_ref = db.collection("agents")
        agent_query = agents_ref.where("cpId", "==", cp_id).stream()
        agent_details = next((doc.to_dict() for doc in agent_query), None)

        # Prepare enquiry data
        enquiry_data = {
            "enquiryId": f"EQA{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "buyerAgentNumber": buyer_agent_number if buyer_agent_number else "Unknown",
            "propertyId": property_id,
            "sellerAgentNumber": agent_details.get("phonenumber", "Unknown") if agent_details else "Unknown",
            "sellerAgentName": agent_details.get("name", "Unknown") if agent_details else "Unknown",
            "cpId": cp_id if cp_id else "Unknown",
            "sellerAgentKAM": agent_details.get("kam", "Unknown") if agent_details else "Unknown",
            "dateOfStatusLastChecked": date_of_status_last_checked,
            "added": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "lastModified": datetime.now().strftime('%Y-%m-%d'),
            "status": property_details.get("status", "Unknown")
        }

        # Save to Google Sheet
        save_to_google_sheet(sheet, enquiry_data)

        return {
            "Property ID": property_id,
            "Seller Agent Name": enquiry_data["sellerAgentName"],
            "Seller Agent Number": enquiry_data["sellerAgentNumber"],
            "Date of Status Last Checked": enquiry_data["dateOfStatusLastChecked"]
        }

    except Exception as e:
        st.error(f"Error fetching and saving data: {e}")
        return None

# Streamlit app
def main():
    st.sidebar.title("Navigation")
    st.title("Property Enquiry System")

    # Initialize Firebase and Google Sheets
    db = init_firebase()
    sheet = init_google_sheets()

    # Form for input
    with st.form("enquiry_form"):
        property_id = st.text_input("Property ID", placeholder="Enter the Property ID")
        buyer_agent_number = st.text_input("Buyer Agent Number (Optional)", placeholder="Enter the Buyer's Phone Number")
        submitted = st.form_submit_button("Submit")

    # Handle form submission
    if submitted:
        if not property_id:
            st.error("Please fill in the Property ID.")
        else:
            with st.spinner("Fetching data..."):
                details = fetch_data_and_save(db, sheet, property_id, buyer_agent_number)
                if details:
                    st.success("Enquiry data saved successfully!")

                    # Enhanced display of fetched details
                    st.subheader("Fetched Details")
                    st.write(f"**Property ID:** `{details['Property ID']}`")
                    st.write(f"**Seller Agent Name:** {details['Seller Agent Name']}")
                    st.write(f"**Seller Agent Number:** {details['Seller Agent Number']}")
                    st.write(f"**Date of Status Last Checked:** {details['Date of Status Last Checked']}")

                    # Prepare copyable details
                    copy_details = (
                        f"Property ID: {details['Property ID']}\n"
                        f"Seller Agent Name: {details['Seller Agent Name']}\n"
                        f"Seller Agent Number: {details['Seller Agent Number']}\n"
                        # f"Date of Status Last Checked: {details['Date of Status Last Checked']}"
                    )

                    # Display the copyable text area
                    st.subheader("Copy Details to Clipboard")
                    components.html(f"""
                        <textarea id="details" style="width: 100%; height: 100px;" readonly>{copy_details}</textarea>
                        <button onclick="navigator.clipboard.writeText(document.getElementById('details').value)"
                                style="padding: 10px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">
                            Copy to Clipboard
                        </button>
                    """, height=150)

if __name__ == "__main__":
    main()
