import os
import re
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import gspread
from datetime import datetime
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Rental Inventory",  
    page_icon="./logo.jpg"  # Use relative path without the leading slash
)

# Force favicon update using HTML
favicon_url = "./logo.jpg"  # Ensure the file exists in your project folder

st.markdown(
    f"""
    <link rel="icon" type="image/jpeg" href="{favicon_url}">
    """,
    unsafe_allow_html=True
)





from dotenv import load_dotenv
load_dotenv()

def format_timestamp(ts):
    return datetime.fromtimestamp(ts).strftime('%d/%b/%Y') if ts else "Unknown"

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
        st.error(f"❌ Error initializing Firebase: {e}")
        st.stop()

@st.cache_resource
def init_google_sheets():
    try:
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
        sheet_id = os.getenv("RENTAL_SHEET_ID")
        if not sheet_id:
            st.error("❌ Google Sheet ID is missing! Check your .env file.")
            return None
        sheet = client.open_by_key(sheet_id).sheet1
        # Updated expected headers with additional columns
        expected_headers = [
            "Enquiry ID",
            "Added",
            "Buyer Agent Number",
            "Buyer Agent Name",
            "Property ID",
            "Property Name",
            "Property Type",
            "Rent Per Month in Lakhs",
            "Configuration",
            "Micromarket",
            "Seller Agent Name",
            "Seller Agent Number",
            "Date of Status Last Checked"
        ]
        existing_headers = sheet.row_values(1)
        if existing_headers != expected_headers:
            sheet.clear()
            sheet.append_row(expected_headers)
        return sheet_id
    except Exception as e:
        st.error(f"❌ Error initializing Google Sheets: {e}")
        st.stop()

# Removed caching here so it always fetches the latest data
def get_last_enquiry_id(sheet_id):
    try:
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
        sheet = client.open_by_key(sheet_id).sheet1
        records = sheet.get_all_records()
        if not records:
            return "RENT0000"
        last_row = records[-1]
        return last_row.get("Enquiry ID", "RENT0000")
    except Exception as e:
        st.error(f"❌ Error fetching last enquiry ID: {e}")
        return "RENT0000"

@st.cache_data(ttl=600)
def fetch_rental_data(_db, property_id, buyer_agent_number, last_enquiry_id):
    try:
        property_id = property_id.upper()
        buyer_agent_number = re.sub(r"[^\d+]", "", buyer_agent_number)
        if not buyer_agent_number.startswith("+91"):
            if buyer_agent_number.startswith("91"):
                buyer_agent_number = f"+{buyer_agent_number}"
            elif len(buyer_agent_number) == 10:
                buyer_agent_number = f"+91{buyer_agent_number}"
            else:
                raise ValueError("Invalid mobile number format")
        rentals_ref = _db.collection("rental-inventories")
        rental_query = rentals_ref.where("propertyId", "==", property_id).stream()
        rental_details = next((doc.to_dict() for doc in rental_query), None)
        if not rental_details:
            st.error("❌ No rental property found for the given Property ID.")
            return None
        seller_agent_number = rental_details.get("agentNumber", "Unknown")
        seller_agent_name = rental_details.get("agentName", "Unknown")
        agents_ref = _db.collection("agents")
        buyer_query = agents_ref.where("phonenumber", "==", buyer_agent_number).stream()
        buyer_details = next((doc.to_dict() for doc in buyer_query), None)
        buyer_agent_name = buyer_details.get("name", "Unknown") if buyer_details else "Unknown"
        prefix = last_enquiry_id[:4]
        numeric_part = int(last_enquiry_id[4:]) + 1
        new_enquiry_id = f"{prefix}{numeric_part:04}"
        # New rental_data dictionary with keys ordered to match the sheet columns
        rental_data = {
            "Enquiry ID": new_enquiry_id,
            "Added": datetime.now().strftime('%d/%b/%Y'),
            "Buyer Agent Number": buyer_agent_number,
            "Buyer Agent Name": buyer_agent_name,
            "Property ID": rental_details.get("propertyId", "Unknown"),
            "Property Name": rental_details.get("propertyName", "Unknown"),
            "Property Type": rental_details.get("propertyType", "Unknown"),
            "Rent Per Month in Lakhs": rental_details.get("rentPerMonthInLakhs", "Unknown"),
            "Configuration": rental_details.get("configuration", "Unknown"),
            "Micromarket": rental_details.get("micromarket", "Unknown"),
            "Seller Agent Name": seller_agent_name,
            "Seller Agent Number": seller_agent_number,
            "Date of Status Last Checked": format_timestamp(rental_details.get("dateOfStatusLastChecked"))
        }
        return rental_data
    except Exception as e:
        st.error(f"❌ Error fetching rental data: {e}")
        return None

def save_enquiry_to_google_sheet(sheet_id, data):
    try:
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
        sheet = client.open_by_key(sheet_id).sheet1
        # Append row using the values in the order of the expected headers
        sheet.append_row(list(data.values()))
        st.success("✅ Enquiry saved successfully!")
    except Exception as e:
        st.error(f"❌ Error saving to Google Sheet: {e}")

def main():
    st.title("🏠 Rental Property Enquiry System")
    db = init_firebase()
    sheet_id = init_google_sheets()
    # Always fetch the latest enquiry id
    last_enquiry_id = get_last_enquiry_id(sheet_id)
    with st.form("rental_enquiry_form"):
        property_id = st.text_input("📌 Property ID", placeholder="Enter Property ID")
        buyer_agent_number = st.text_input("📞 Buyer Agent Number", placeholder="Enter Buyer Agent's Phone Number")
        submitted = st.form_submit_button("🔍 Fetch Details")
    if submitted:
        if not property_id or not buyer_agent_number:
            st.error("❌ Please provide both Property ID and Buyer Agent Number.")
        else:
            with st.spinner("Fetching data..."):
                rental_data = fetch_rental_data(db, property_id, buyer_agent_number, last_enquiry_id)
                if rental_data:
                    save_enquiry_to_google_sheet(sheet_id, rental_data)
                    st.success("✅ Rental details fetched successfully!")
                    st.subheader(f"🏠 {rental_data['Property Name']} ({rental_data['Property ID']})")
                    st.write(f"**Seller Agent:** {rental_data['Seller Agent Name']} ({rental_data['Seller Agent Number']})")
                    st.write(f"**Date of Status Last Checked:** {rental_data['Date of Status Last Checked']}")
                    
                    # Updated copy text with additional fields
                    copy_text = (
                        f"🏠 Property: {rental_data['Property Name']} ({rental_data['Property ID']})\n"
                        f"🏢 Property Type: {rental_data.get('Property Type', 'Unknown')}\n"
                        f"💰 Rent Per Month in Lakhs: {rental_data.get('Rent Per Month in Lakhs', 'Unknown')}\n"
                        f"🏘 Configuration: {rental_data.get('Configuration', 'Unknown')}\n"
                        f"📍 Micromarket: {rental_data.get('Micromarket', 'Unknown')}\n"
                        f"📞 Seller Agent: {rental_data['Seller Agent Name']} ({rental_data['Seller Agent Number']})\n"
                        f"🗓 Last Checked: {rental_data['Date of Status Last Checked']}"
                    )
                    st.subheader("📋 Copy Details to Clipboard")
                    components.html(f"""
                        <textarea id="details" style="width: 100%; height: 150px;" readonly>{copy_text}</textarea>
                        <button onclick="navigator.clipboard.writeText(document.getElementById('details').value)"
                                style="padding: 10px; background-color: rgb(0, 128, 0); color: white; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px;">
                            📋 Copy to Clipboard
                        </button>
                    """, height=220)

if __name__ == "__main__":
    main()
