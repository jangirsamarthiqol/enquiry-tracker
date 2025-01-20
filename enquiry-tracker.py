import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import toml
from datetime import datetime
import streamlit.components.v1 as components  # For embedding HTML/JS

# Load credentials from TOML file
try:
    with open("combined-service-accounts.toml", "r") as toml_file:
        config = toml.load(toml_file)
except FileNotFoundError:
    st.error("TOML file not found. Please ensure 'combined-service-accounts.toml' exists.")
    st.stop()
except toml.TomlDecodeError as e:
    st.error(f"Error parsing TOML file: {e}")
    st.stop()

# Firebase initialization using TOML credentials
try:
    firebase_config = config["firebase"]
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except KeyError:
    st.error("The 'firebase' section is missing in the TOML file.")
    st.stop()
except Exception as e:
    st.error(f"Error initializing Firebase: {e}")
    st.stop()

# Google Sheets Setup using TOML credentials
try:
    sheets_config = config["google_sheets"]
    SHEET_ID = "1mt-Uj3CvVgLsEBibwv34wwhbcoMjI0Co_ReownIYjSA"  # Replace with your Google Sheet ID
    SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    CREDS = ServiceAccountCredentials.from_json_keyfile_dict(sheets_config, SCOPE)
    client = gspread.authorize(CREDS)
    sheet = client.open_by_key(SHEET_ID).sheet1
except KeyError:
    st.error("The 'google_sheets' section is missing in the TOML file.")
    st.stop()
except Exception as e:
    st.error(f"Error initializing Google Sheets: {e}")
    st.stop()

# Initialize Google Sheet if empty
def init_google_sheet():
    try:
        existing_data = sheet.get_all_records()
        if not existing_data:
            sheet.append_row([
                "Enquiry ID",
                "Buyer Agent KAM", "Property ID", "Seller Agent Number", "Seller Agent Name", "CP_ID",
                "Seller Agent KAM", "Date of Status Last Checked", "Added",
                "Last Modified", "Status"
            ])
    except Exception as e:
        st.error(f"Error initializing Google Sheet: {e}")

# Save enquiry data to Google Sheet
def save_to_google_sheet(enquiry_data):
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

# Fetch data from Firebase and save to Google Sheet
def fetch_data_and_save(property_id, buyer_agent_number):
    try:
        # Convert property_id to uppercase for case-insensitive handling
        property_id = property_id.upper()

        # Query ACN123 collection to fetch property details
        inventories_ref = db.collection("ACN123")
        inventory_query = inventories_ref.where("propertyId", "==", property_id).stream()

        property_details = None
        for doc in inventory_query:
            property_details = doc.to_dict()
            break

        if not property_details:
            st.error("No property found for the given Property ID.")
            return None

        # Extract property details
        cp_id = property_details.get("cpCode")
        date_of_status_last_checked = property_details.get("dateOfStatusLastChecked", "Unknown")

        # Query agents collection to fetch agent details
        agents_ref = db.collection("agents")
        agent_query = agents_ref.where("cpId", "==", cp_id).stream()

        agent_details = None
        for agent_doc in agent_query:
            agent_details = agent_doc.to_dict()
            break

        if not agent_details:
            st.error("No agent found for the given CP_ID.")
            return None

        # Extract agent details
        seller_agent_name = agent_details.get("name", "Unknown")
        seller_agent_number = agent_details.get("phonenumber", "Unknown")

        # Prepare enquiry data
        enquiry_data = {
            "enquiryId": f"EQA{datetime.now().strftime('%Y%m%d%H%M%S')}",  # Unique enquiry ID
            "buyerAgentNumber": buyer_agent_number,
            "propertyId": property_id,
            "sellerAgentNumber": seller_agent_number,
            "sellerAgentName": seller_agent_name,
            "cpId": cp_id,
            "sellerAgentKAM": agent_details.get("kam", "Unknown"),
            "dateOfStatusLastChecked": date_of_status_last_checked,
            "added": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "lastModified": datetime.now().strftime('%Y-%m-%d'),
            "status": property_details.get("status", "")
        }

        # Save enquiry data to Google Sheet
        save_to_google_sheet(enquiry_data)

        # Return minimal details for UI display
        return {
            "Property ID": property_id,
            "Seller Agent Name": seller_agent_name,
            "Seller Agent Number": seller_agent_number,
            "Date of Status Last Checked": date_of_status_last_checked
        }

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# Streamlit App
def main():
    st.sidebar.title("Navigation")
    st.sidebar.markdown("Use this tool to manage and track property enquiries.")
    st.title("Property Enquiry System")

    # Initialize Google Sheet
    init_google_sheet()

    # Form for input
    with st.form("enquiry_form", clear_on_submit=True):
        st.subheader("Enter Enquiry Details")
        property_id = st.text_input("Property ID", placeholder="Enter Property ID")
        buyer_agent_number = st.text_input("Buyer Agent Number", placeholder="Enter buyer's phone number")
        submitted = st.form_submit_button("Submit")

    if submitted:
        if not property_id or not buyer_agent_number:
            st.error("Please fill in all fields.")
        else:
            with st.spinner("Fetching seller agent details..."):
                seller_details = fetch_data_and_save(property_id, buyer_agent_number)
                if seller_details:
                    st.success("Details fetched successfully!")

                    # Display the fetched details
                    st.header("Fetched Details")
                    st.write(f"**Property ID:** `{seller_details['Property ID']}`")
                    st.write(f"**Seller Agent Name:** {seller_details['Seller Agent Name']}")
                    st.write(f"**Seller Agent Number:** {seller_details['Seller Agent Number']}")
                    st.write(f"**Date of Status Last Checked:** {seller_details['Date of Status Last Checked']}")

if __name__ == "__main__":
    main()
