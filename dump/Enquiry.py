import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import streamlit.components.v1 as components  # For embedding HTML/JS

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("service-account.json")  # Path to Firebase Admin SDK JSON
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Google Sheets Setup
SHEET_ID = "1mt-Uj3CvVgLsEBibwv34wwhbcoMjI0Co_ReownIYjSA"  # Replace with your Google Sheet ID
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("enquiry-tracking-153a65032a1b.json", SCOPE)
client = gspread.authorize(CREDS)
sheet = client.open_by_key(SHEET_ID).sheet1

# Initialize Google Sheet if empty
def init_google_sheet():
    existing_data = sheet.get_all_records()
    if not existing_data:
        sheet.append_row([
            "Enquiry ID",
            "Buyer Agent KAM", "Property ID", "Seller Agent Number", "Seller Agent Name","CP_ID",
            "Seller Agent KAM", "Date of Status Last Checked","Added",
            "Last Modified", "Status"
        ])

# Save enquiry data to Google Sheet
def save_to_google_sheet(enquiry_data):
    try:
        sheet.append_row([
            enquiry_data.get("enquiryId", ""),
            enquiry_data.get("buyerAgentNumber", ""),
       #      enquiry_data.get("buyerAgentName", ""),
       #      enquiry_data.get("buyerAgentKAM", ""),
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

        buyer_agent_name = agent_details.get("name", "Unknown")
       #  buyer_agent_number = agent_details.get("phonenumber", "Unknown")

        # Prepare enquiry data
        enquiry_data = {
            "enquiryId": f"EQA{datetime.now().strftime('%Y%m%d%H%M%S')}",  # Unique enquiry ID
            "buyerAgentNumber": buyer_agent_number,
       #      "buyerAgentName": buyer_agent_name,
       #      "buyerAgentKAM": agent_details.get("kam", "Unknown"),
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

                    # Prepare copyable details
                    details_copy = (
                        f"Property ID: {seller_details['Property ID']}\n"
                        f"Seller Agent Name: {seller_details['Seller Agent Name']}\n"
                        f"Seller Agent Number: {seller_details['Seller Agent Number']}"
                    )

                    # Add Copy to Clipboard Button with HTML and JS
                    st.write("### Copy Details to Clipboard")
                    components.html(f"""
                    <textarea id="details" style="width: 100%; height: 100px;" readonly>{details_copy}</textarea>
                    <button onclick="navigator.clipboard.writeText(document.getElementById('details').value)"
                            style="padding: 10px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        Copy to Clipboard
                    </button>
                    """, height=150)

if __name__ == "__main__":
    main()
