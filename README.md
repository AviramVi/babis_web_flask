# Babis Web Flask Application

## Overview
The Babis Web Flask application is a web-based version of the original Babis application, designed to manage instructors and clients efficiently. This application utilizes Flask as the web framework and integrates with Google Sheets for data management.

## Project Structure
The project is organized as follows:

```
babis_web_flask
├── app.py                     # Main entry point of the Flask application
├── requirements.txt           # Lists dependencies required for the project
├── README.md                  # Documentation for the project
├── .env                       # Environment variables for configuration
├── SERVICE_ACCOUNT_FILE.json   # Service account credentials for Google Sheets
├── static                     # Static files (CSS, JS)
│   ├── css
│   │   └── style.css          # CSS styles for the web application
│   └── js
│       └── main.js            # JavaScript code for client-side functionality
├── templates                  # HTML templates for the web application
│   ├── base.html              # Base template with common structure
│   ├── dashboard.html         # Layout for the dashboard page
│   ├── instructors.html       # Layout for the instructors page
│   ├── clients_private.html   # Layout for the private clients page
│   ├── clients_institutional.html # Layout for the institutional clients page
│   ├── payments.html          # Layout for the payments page
│   ├── debts.html             # Layout for the debts page
│   └── year_board.html        # Layout for the year board page
└── utils                      # Utility functions
    └── google_sheets.py       # Functions for interacting with Google Sheets
```

## Setup Instructions
1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd babis_web_flask
   ```

2. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the root directory and add your configuration variables, such as API keys and other sensitive information.

5. **Add your Google Sheets service account credentials**:
   Place your `SERVICE_ACCOUNT_FILE.json` in the root directory.

## Usage
To run the application, execute the following command:
```bash
python app.py
```
The application will be accessible at `http://127.0.0.1:5000`.

## Features
- Manage instructors and clients with ease.
- Interactive dashboard for quick access to important information.
- Integration with Google Sheets for data storage and retrieval.
- Responsive design for accessibility on various devices.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.