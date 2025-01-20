Here's a GitHub `README.md` file for your project:

```markdown
# Property Enquiry Tracking System

A web application built with **Streamlit**, **Google Sheets**, and **Firebase Firestore** to manage and track property enquiries efficiently.

---

## Features

- **Property Management**: Search and retrieve property details using a unique property ID.
- **Buyer and Seller Agent Details**: Fetch associated buyer and seller agent details from Firestore.
- **Google Sheets Integration**: Save and manage enquiry data in Google Sheets.
- **Responsive UI**: User-friendly interface with streamlined workflows.
- **Data Validation**: Ensure input correctness and display appropriate error messages.
- **Copy to Clipboard**: Easily copy fetched details for sharing.

---

## Technologies Used

- **Frontend**: [Streamlit](https://streamlit.io/)
- **Backend**: [Firebase Firestore](https://firebase.google.com/docs/firestore)
- **Google Sheets API**: For saving and managing enquiry data.

---

## Installation

### Prerequisites

- Python 3.9 or higher
- Firebase Project with Firestore enabled
- Service account keys for Firebase and Google Sheets API

### Clone the Repository

```bash
git clone https://github.com/your-username/property-enquiry-tracking.git
cd property-enquiry-tracking
```

### Install Dependencies

Create a virtual environment and install the required packages:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Add Service Account Keys

1. Download the Firebase Admin SDK service account key and rename it to `service-account.json`.
2. Download the Google Sheets API credentials and rename them to `enquiry-tracking-153a65032a1b.json`.
3. Place both files in the project directory.

---

## Usage

### Run the Application

```bash
streamlit run app.py
```

### How It Works

1. **Enter Details**: Fill in the `Property ID` and `Buyer Agent Number` fields.
2. **Submit Query**: Click the **Submit** button to fetch the details.
3. **View Results**: See the fetched property and agent details on the UI.
4. **Save to Google Sheets**: Data is automatically saved to a linked Google Sheet.

---

## File Structure

```
property-enquiry-tracking/
├── app.py                  # Main application script
├── service-account.json    # Firebase service account key
├── enquiry-tracking-153a65032a1b.json # Google Sheets API credentials
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
```

---

## Google Sheets Format

| **Enquiry ID** | **Buyer Agent Number** | **Property ID** | **Seller Agent Name** | **Seller Agent Number** | **CP_ID** | **Date of Status Last Checked** | **Added** | **Last Modified** | **Status** |
|----------------|-------------------------|------------------|------------------------|--------------------------|-----------|--------------------------------|-----------|-------------------|------------|

---

## Firestore Structure

### Collection: `ACN123` (Properties)

- `propertyId`: String (unique identifier for a property)
- `cpCode`: String (associated seller agent code)
- `status`: String
- `dateOfStatusLastChecked`: Date

### Collection: `agents` (Agents)

- `cpId`: String (unique seller agent code)
- `phonenumber`: String (stored with `+91` prefix)
- `name`: String
- `kam`: String (Key Account Manager)

---

## Contributions

Contributions are welcome! Feel free to fork this repository and submit pull requests.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Contact

For any questions or issues, please contact [your-email@example.com](mailto:your-email@example.com).
```

### Customization
Replace placeholders like `your-username`, `your-email@example.com`, and `LICENSE` details as per your project. Let me know if you want to add any specific details or sections!