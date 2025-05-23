from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import gspread
import os
from datetime import datetime

load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_gspread_client():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return gspread.authorize(creds)

def get_sheet_data(sheet_name):
    """Fetch both headers and data from a specific worksheet."""
    gc = get_gspread_client()
    worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
    
    # Get headers from first row
    headers = worksheet.row_values(1)
    
    # Get all records as dictionaries
    records = worksheet.get_all_records()
    
    return headers, records

def fetch_instructors(sheet_name):
    """Fetch instructors data using get_sheet_data."""
    headers, records = get_sheet_data(sheet_name)
    return records

def fetch_clients(sheet_name):
    """Fetch clients data using get_sheet_data."""
    headers, records = get_sheet_data(sheet_name)
    return records

def update_instructor(sheet_name, row, updates):
    """Update multiple cells for an instructor in a single batch operation.
    
    Args:
        sheet_name: Name of the worksheet
        row: Row number (1-indexed)
        updates: Dictionary mapping column indices (1-indexed) to values
    """
    gc = get_gspread_client()
    worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)

    # Prepare the data in the correct format for batch update
    values = [updates.get(col, '') for col in sorted(updates.keys())]

    # Update the row with the new values
    worksheet.update(f"A{row}:F{row}", [values])

def add_instructor(sheet_name, instructor_data):
    gc = get_gspread_client()
    worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
    worksheet.append_row(instructor_data)

def fetch_billing_data():
    """Fetch billing data from the dedicated billing spreadsheet."""
    try:
        gc = get_gspread_client()
        # Use the dedicated billing spreadsheet ID
        billing_spreadsheet_id = os.getenv('billing_SPREADSHEET_ID')
        worksheet = gc.open_by_key(billing_spreadsheet_id).sheet1  # Get first sheet
        
        # Get all records including headers
        all_values = worksheet.get_all_values()
        if not all_values:
            return [], []
            
        headers = all_values[0]  # First row contains headers
        records = [dict(zip(headers, row)) for row in all_values[1:]]  # Convert to dict
        
        # Sort records by date (newest first)
        sorted_records = sorted(
            records,
            key=lambda x: datetime.strptime(x['תאריך'], '%d/%m/%Y'),
            reverse=True
        )
        
        return headers, sorted_records
    except Exception as e:
        print(f"Error fetching billing data: {e}")
        return [], []

def get_billing_worksheets():
    """Fetch only month-named worksheets from billing spreadsheet."""
    hebrew_months = [
        "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
        "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
    ]
    
    try:
        gc = get_gspread_client()
        billing_spreadsheet_id = os.getenv('billing_SPREADSHEET_ID')
        spreadsheet = gc.open_by_key(billing_spreadsheet_id)
        # Filter worksheets that start with month names
        return [ws.title for ws in spreadsheet.worksheets() 
                if any(ws.title.startswith(month) for month in hebrew_months)]
    except Exception as e:
        print(f"Error fetching worksheet names: {e}")
        return []

def fetch_billing_data(worksheet_name=None):
    """Fetch billing data from specific worksheet."""
    try:
        gc = get_gspread_client()
        billing_spreadsheet_id = os.getenv('billing_SPREADSHEET_ID')
        spreadsheet = gc.open_by_key(billing_spreadsheet_id)
        
        # If no worksheet specified, use first available month worksheet
        if not worksheet_name:
            worksheet_names = get_billing_worksheets()
            worksheet_name = worksheet_names[0] if worksheet_names else None
            
        if not worksheet_name:
            return [], []
            
        worksheet = spreadsheet.worksheet(worksheet_name)
        all_values = worksheet.get_all_values()
        
        if not all_values:
            return [], []
            
        headers = all_values[0]
        records = [dict(zip(headers, row)) for row in all_values[1:]]
        
        return headers, records
    except Exception as e:
        print(f"Error fetching billing data: {e}")
        return [], []

def get_payment_worksheets():
    """Fetch only month-named worksheets from the payments spreadsheet."""
    hebrew_months = [
        "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
        "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
    ]
    try:
        gc = get_gspread_client()
        payment_spreadsheet_id = os.getenv('payment_SPREADSHEET_ID')
        spreadsheet = gc.open_by_key(payment_spreadsheet_id)
        return [ws.title for ws in spreadsheet.worksheets()
                if any(ws.title.startswith(month) for month in hebrew_months)]
    except Exception as e:
        print(f"Error fetching payment worksheet names: {e}")
        return []

def fetch_payment_data(worksheet_name=None):
    """Fetch payment data from a specific worksheet in the payments spreadsheet."""
    try:
        gc = get_gspread_client()
        payments_spreadsheet_id = os.getenv('payments_SPREADSHEET_ID')
        
        if worksheet_name:
            worksheet = gc.open_by_key(payments_spreadsheet_id).worksheet(worksheet_name)
        else:
            worksheet = gc.open_by_key(payments_spreadsheet_id).sheet1
        
        # Get all records including headers
        all_values = worksheet.get_all_values()
        if not all_values or len(all_values) < 2:  # Need at least headers and one data row
            return [], []
            
        headers = all_values[0]  # First row contains headers
        records = [dict(zip(headers, row)) for row in all_values[1:]]  # Convert to dict
        
        return headers, records
    except Exception as e:
        print(f"Error fetching payment data: {e}")
        return [], []

def append_row(sheet_name, row_data):
    """Append a new row to the specified worksheet.
    
    Args:
        sheet_name: Name of the worksheet
        row_data: List of values to append
        
    Returns:
        The result of the append operation
    """
    try:
        gc = get_gspread_client()
        worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        result = worksheet.append_row(row_data)
        return result
    except Exception as e:
        print(f"Error appending row to {sheet_name}: {e}")
        return None

def update_row(sheet_name, row_number, updates):
    """Update specific cells in a row.
    
    Args:
        sheet_name: Name of the worksheet
        row_number: Row number (1-indexed)
        updates: Dictionary of {column_letter: value} pairs to update
        
    Returns:
        The result of the update operation
    """
    try:
        gc = get_gspread_client()
        worksheet = gc.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
        
        # Convert column letters to A1 notation (e.g., {'A': 'value'} -> 'A2')
        cell_updates = []
        for col_letter, value in updates.items():
            cell = f"{col_letter.upper()}{row_number}"
            cell_updates.append({
                'range': cell,
                'values': [[value]]
            })
        
        if cell_updates:
            worksheet.batch_update(cell_updates)
            return True
        return False
    except Exception as e:
        print(f"Error updating row {row_number} in {sheet_name}: {e}")
        return False