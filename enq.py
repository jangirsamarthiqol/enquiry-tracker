import os
import re
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
@st.cache_resource
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
                "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
            })
            firebase_admin.initialize_app(firebase_cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Error initializing Firebase: {e}")
        st.stop()

# Initialize Google Sheets
@st.cache_resource
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
            "client_x509_cert_url": os.getenv("GSPREAD_CLIENT_X509_CERT_URL")
        }
        client = gspread.service_account_from_dict(google_creds)
        sheet = client.open_by_key(os.getenv("GSPREAD_SHEET_ID")).sheet1

        # Initialize the sheet if empty
        if not sheet.get_all_records():
            sheet.append_row([
                "Enquiry ID", "Added", "Buyer Agent Number", "CP_ID", "Buyer Agent Name", "Buyer Agent KAM",
                "Property ID", "Property Name", "Seller Agent Number", "Seller Agent Name", "Seller Agent KAM",
                "# Times Property ID Enquired", "Date of Status Last Checked for the Inventory Enquired", 
                "Last Modified", "Status"
            ])
        return sheet
    except Exception as e:
        st.error(f"Error initializing Google Sheets: {e}")
        st.stop()

# Normalize mobile number
def normalize_mobile_number(number):
    """
    Normalize a mobile number by ensuring it starts with '+91' and removing unwanted characters.
    """
    cleaned_number = re.sub(r"[^\d+]", "", number)  # Remove non-numeric characters except '+'
    if not cleaned_number.startswith("+91"):
        if cleaned_number.startswith("91"):
            cleaned_number = f"+{cleaned_number}"
        elif len(cleaned_number) == 10:  # Case: 10-digit mobile number
            cleaned_number = f"+91{cleaned_number}"
        else:
            raise ValueError("Invalid mobile number format")
    return cleaned_number

# Save data to Google Sheet (Batch Processing)
def batch_save_to_google_sheet(sheet, data_list):
    try:
        for data in data_list:
            sheet.append_row([
                data.get("enquiryId", ""),
                data.get("added", ""),
                data.get("buyerAgentNumber", ""),
                data.get("cpId", ""),
                data.get("buyerAgentName", ""),
                data.get("buyerAgentKAM", ""),
                data.get("propertyId", ""),
                data.get("propertyName", ""),  # Correct key for property name
                data.get("sellerAgentNumber", ""),
                data.get("sellerAgentName", ""),
                data.get("sellerAgentKAM", ""),
                data.get("timesEnquired", ""),
                data.get("dateOfStatusLastChecked", ""),
                data.get("lastModified", ""),
                data.get("status", "")
            ])
    except Exception as e:
        st.error(f"Error saving to Google Sheet: {e}")

# Fetch the last enquiry ID dynamically from Google Sheets
def get_last_enquiry_id(sheet):
    try:
        records = sheet.get_all_records()
        if not records:
            return "EQB1437"  # Default starting ID
        last_row = records[-1]
        return last_row.get("Enquiry ID", "EQB1437")
    except Exception as e:
        st.error(f"Error fetching the last enquiry ID: {e}")
        return "EQB1437"  # Fallback in case of error

# Fetch data from Firebase and save to Google Sheets
@st.cache_data(ttl=600)
def fetch_data_and_save(_db, property_id, buyer_agent_number, last_enquiry_id):
    try:
        property_id = property_id.upper()

        # Normalize the buyer agent number
        try:
            buyer_agent_number = normalize_mobile_number(buyer_agent_number)
        except ValueError as e:
            st.error(f"Invalid Buyer Agent Number: {e}")
            return None

        # Fetch property details
        inventories_ref = _db.collection("ACN123")
        inventory_query = inventories_ref.where("propertyId", "==", property_id).stream()
        property_details = next((doc.to_dict() for doc in inventory_query), None)

        if not property_details:
            st.error("No property found for the given Property ID.")
            return None

        # Extract details
        property_name = property_details.get("nameOfTheProperty", "Unknown")  # Use correct key for property name
        unix_timestamp = property_details.get("dateOfStatusLastChecked")
        date_of_status_last_checked = datetime.fromtimestamp(unix_timestamp).strftime('%Y-%m-%d') if unix_timestamp else "Unknown"

        # Fetch seller agent details
        cp_id = property_details.get("cpCode")
        agents_ref = _db.collection("agents")
        seller_query = agents_ref.where("cpId", "==", cp_id).stream()
        seller_details = next((doc.to_dict() for doc in seller_query), None)

        # Fetch buyer agent details
        buyer_query = agents_ref.where("phonenumber", "==", buyer_agent_number).stream()
        buyer_details = next((doc.to_dict() for doc in buyer_query), None)

        # Generate next enquiry ID
        prefix = last_enquiry_id[:3]
        numeric_part = int(last_enquiry_id[3:]) + 1
        new_enquiry_id = f"{prefix}{numeric_part:04}"

        # Prepare enquiry data
        enquiry_data = {
            "enquiryId": new_enquiry_id,
            "added": datetime.now().strftime('%d/%b/%Y'),  # Format: 26/Jan/2025
            "buyerAgentNumber": buyer_agent_number,
            "cpId": buyer_details.get("cpId", "Unknown") if buyer_details else "Unknown",
            "buyerAgentName": buyer_details.get("name", "Unknown") if buyer_details else "Unknown",
            "buyerAgentKAM": buyer_details.get("kam", "Unknown") if buyer_details else "Unknown",
            "propertyId": property_id,
            "propertyName": property_name,
            "sellerAgentNumber": seller_details.get("phonenumber", "Unknown") if seller_details else "Unknown",
            "sellerAgentName": seller_details.get("name", "Unknown") if seller_details else "Unknown",
            "sellerAgentKAM": seller_details.get("kam", "Unknown") if seller_details else "Unknown",
            "timesEnquired": 1,
            "dateOfStatusLastChecked": date_of_status_last_checked,
            "lastModified": datetime.now().strftime('%Y-%m-%d'),
            "status": property_details.get("status", "Unknown")
        }

        return enquiry_data

    except Exception as e:
        st.error(f"Error fetching and saving data: {e}")
        return None

# Streamlit app
def main():
    st.sidebar.title("Navigation")
    st.sidebar.markdown("[Micromarket Finder](https://micromarket-finder.onrender.com/)")
    st.title("Property Enquiry System")

    # Initialize Firebase and Google Sheets
    db = init_firebase()
    sheet = init_google_sheets()

    # Get the last enquiry ID
    last_enquiry_id = get_last_enquiry_id(sheet)

    # Form for input
    with st.form("enquiry_form"):
        property_id = st.text_input("Property ID", placeholder="Enter the Property ID")
        buyer_agent_number = st.text_input("Buyer Agent Number", placeholder="Enter the Buyer's Phone Number")
        submitted = st.form_submit_button("Submit")

    # Handle form submission
    if submitted:
        if not property_id or not buyer_agent_number:
            st.error("Please fill in all required fields.")
        else:
            with st.spinner("Fetching data..."):
                enquiry_data = fetch_data_and_save(db, property_id, buyer_agent_number, last_enquiry_id)
                if enquiry_data:
                    # Save to Google Sheet in batch
                    batch_save_to_google_sheet(sheet, [enquiry_data])

                    st.success("Enquiry data saved successfully!")

                    # Display fetched details
                    st.subheader("Fetched Details")
                    st.write(f"**Property ID:** `{enquiry_data['propertyId']}`")
                    st.write(f"**Property Name:** `{enquiry_data['propertyName']}`")
                    st.write(f"**Seller Agent Name:** {enquiry_data['sellerAgentName']}")
                    st.write(f"**Seller Agent Number:** {enquiry_data['sellerAgentNumber']}")
                    st.write(f"**Date of Status Last Checked:** {enquiry_data['dateOfStatusLastChecked']}")

                    # Copyable details
                    copy_details = (
                        f"Property ID: {enquiry_data['propertyId']}\n"
                        f"Property Name: {enquiry_data['propertyName']}\n"
                        f"Seller Agent Name: {enquiry_data['sellerAgentName']}\n"
                        f"Seller Agent Number: {enquiry_data['sellerAgentNumber']}"
                    )

                    st.subheader("Copy Details to Clipboard")
                    components.html(f"""
                        <textarea id="details" style="width: 100%; height: 100px;" readonly>{copy_details}</textarea>
                        <button onclick="navigator.clipboard.writeText(document.getElementById('details').value)"
                                style="padding: 10px; background-color:rgb(7, 58, 0); color: white; border: none; border-radius: 5px; cursor: pointer;">
                            Copy to Clipboard
                        </button>
                    """, height=150)

    st.markdown("### View Enquiry Sheet")
    st.markdown(
        "[Open Google Sheet](https://docs.google.com/spreadsheets/d/1mt-Uj3CvVgLsEBibwv34wwhbcoMjI0Co_ReownIYjSA/edit?gid=0) ",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
