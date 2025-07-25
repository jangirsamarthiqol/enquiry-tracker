import os
import re
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import gspread
from datetime import datetime
import streamlit.components.v1 as components
from dotenv import load_dotenv

st.set_page_config(
    page_title="Rental Inventory",
    page_icon="./logo.jpg",
)

# favicon
st.markdown(
    '<link rel="icon" type="image/jpeg" href="./logo.jpg">',
    unsafe_allow_html=True
)

load_dotenv()

def format_timestamp(ts):
    # ts might be a UNIX‑timestamp (int/float), a string number, 
    # a Python datetime, or something else.
    if not ts:
        return "Unknown"
    # 1) If it’s already a datetime:
    if hasattr(ts, "strftime"):
        return ts.strftime('%d/%b/%Y')
    # 2) If it’s a string that represents a number:
    try:
        ts_val = float(ts)
    except (TypeError, ValueError):
        return "Unknown"
    # 3) Now it’s a float or int:
    try:
        return datetime.fromtimestamp(ts_val).strftime('%d/%b/%Y')
    except Exception:
        return "Unknown"


@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred = {
            "type": "service_account",
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/v1/certs",
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
        }
        firebase_admin.initialize_app(credentials.Certificate(cred))
    return firestore.client()

@st.cache_resource
def init_google_sheet():
    gcreds = {
        "type": "service_account",
        "project_id": os.getenv("GSPREAD_PROJECT_ID"),
        "private_key_id": os.getenv("GSPREAD_PRIVATE_KEY_ID"),
        "private_key": os.getenv("GSPREAD_PRIVATE_KEY", "").replace("\\n", "\n"),
        "client_email": os.getenv("GSPREAD_CLIENT_EMAIL"),
        "client_id": os.getenv("GSPREAD_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/v1/certs",
        "client_x509_cert_url": os.getenv("GSPREAD_CLIENT_X509_CERT_URL")
    }
    client = gspread.service_account_from_dict(gcreds)

    # try by key, fallback to sheet title
    try:
        sh = client.open_by_key(os.getenv("RENTAL_SHEET_ID"))
    except gspread.exceptions.SpreadsheetNotFound:
        sh = client.open("Enquiry Tracking Rental")

    try:
        sheet = sh.worksheet("Sheet1")
    except gspread.exceptions.WorksheetNotFound:
        st.error("❌ Rename a tab exactly to 'Sheet1'")
        st.stop()

    headers = [
        "Enquiry ID", "Added", "Buyer Agent Number", "Buyer Agent CPID",
        "Buyer Agent Name", "Property ID", "Property Name", "Property Type",
        "Rent Per Month in Lakhs", "Configuration", "Micromarket",
        "Seller Agent Name", "Seller Agent Number", "Seller Agent CPID",
        "Date of Status Last Checked"
    ]
    if sheet.row_values(1) != headers:
        sheet.clear()
        sheet.append_row(headers)

    return sheet

def get_last_enquiry_id(sheet):
    recs = sheet.get_all_records()
    return recs[-1].get("Enquiry ID", "RENT2000") if recs else "RENT2000"

@st.cache_data(ttl=600)
def fetch_rental_data(_db, pid, ban, last_id):
    pid = pid.strip().upper()
    num = re.sub(r"[^\d+]", "", ban.strip())
    if num.startswith("+"):
        if not num.startswith("+91"):
            num = "+" + num.lstrip("+")
    elif len(num) == 10:
        num = "+91" + num

    rentals = _db.collection("acnRentalTemp").where("propertyId", "==", pid).stream()
    rd = next((d.to_dict() for d in rentals), None)
    if not rd:
        st.error("❌ No rental property for that ID.")
        return

    seller_num = rd.get("agentNumber", "Unknown")
    seller_name = rd.get("agentName", "Unknown")

    agents = _db.collection("acnAgents")
    bd = next((d.to_dict() for d in agents.where("phoneNumber", "==", num).stream()), {})
    sd = next((d.to_dict() for d in agents.where("phoneNumber", "==", seller_num).stream()), {})

    prefix, seq = last_id[:4], int(last_id[4:]) + 1
    new_id = f"{prefix}{seq:04}"

    return {
        "Enquiry ID": new_id,
        "Added": datetime.now().strftime('%d/%b/%Y'),
        "Buyer Agent Number": num,
        "Buyer Agent CPID": bd.get("cpId", "Unknown"),
        "Buyer Agent Name": bd.get("name", "Unknown"),
        "Property ID": rd.get("propertyId", "Unknown"),
        "Property Name": rd.get("propertyName", "Unknown"),
        "Property Type": rd.get("propertyType", "Unknown"),
        "Rent Per Month in Lakhs": rd.get("rentPerMonthInLakhs", "Unknown"),
        "Configuration": rd.get("configuration", "Unknown"),
        "Micromarket": rd.get("micromarket", "Unknown"),
        "Seller Agent Name": seller_name,
        "Seller Agent Number": seller_num,
        "Seller Agent CPID": sd.get("cpId", "Unknown"),
        "Date of Status Last Checked": format_timestamp(rd.get("dateOfStatusLastChecked"))
    }

def save_to_sheet(sheet, data):
    sheet.append_row(list(data.values()))

def main():
    st.title("🏠 Rental Property Enquiry System")
    db = init_firebase()
    sheet = init_google_sheet()
    last_id = get_last_enquiry_id(sheet)

    with st.form("f"):
        pid = st.text_input("📌 Property ID")
        ban = st.text_input("📞 Buyer Agent Number")
        go = st.form_submit_button("🔍 Fetch Details")

    if go:
        if not pid or not ban:
            st.error("❌ Fill both fields")
            return

        with st.spinner("Fetching…"):
            rd = fetch_rental_data(db, pid, ban, last_id)
            if rd:
                save_to_sheet(sheet, rd)
                st.success("✅ Rental details fetched successfully!")
                st.subheader(f"🏠 {rd['Property Name']} ({rd['Property ID']})")
                st.write(f"**Seller Agent:** {rd['Seller Agent Name']} ({rd['Seller Agent Number']})")
                st.write(f"**Date of Status Last Checked:** {rd['Date of Status Last Checked']}")

                copy_text = (
                    f"🏠 Property: {rd['Property Name']} ({rd['Property ID']})\n"
                    f"🏢 Property Type: {rd.get('Property Type', 'Unknown')}\n"
                    f"💰 Rent Per Month in Lakhs: {rd.get('Rent Per Month in Lakhs', 'Unknown')}\n"
                    f"🏘 Configuration: {rd.get('Configuration', 'Unknown')}\n"
                    f"📍 Micromarket: {rd.get('Micromarket', 'Unknown')}\n"
                    f"📞 Seller Agent: {rd['Seller Agent Name']} ({rd['Seller Agent Number']})\n"
                    f"🗓 Last Checked: {rd['Date of Status Last Checked']}"
                )
                st.subheader("📋 Copy Details to Clipboard")
                components.html(f"""
                    <textarea id="details" style="width:100%;height:150px;" readonly>{copy_text}</textarea>
                    <button onclick="navigator.clipboard.writeText(document.getElementById('details').value)"
                            style="padding:10px;background-color:#28a745;color:white;border:none;border-radius:5px;cursor:pointer;margin-top:10px;">
                        📋 Copy to Clipboard
                    </button>
                """, height=220)

if __name__ == "__main__":
    main()
