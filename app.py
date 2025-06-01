from flask import Flask, render_template, request, redirect, url_for, jsonify, session, g
import os
import gspread
from dotenv import load_dotenv
from utils.google_sheets import (
    fetch_instructors,
    fetch_clients,
    update_instructor,
    add_instructor,
    get_sheet_data,
    fetch_billing_data,
    get_billing_worksheets,
    get_payment_worksheets,
    fetch_payment_data,
    append_row,
    update_row,
    get_gspread_client
)
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import calendar as pycalendar
import pytz
from datetime import datetime, timedelta, date
import os
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from time import time

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session
load_dotenv()

@app.context_processor
def inject_now():
    """Make 'now' available to all templates."""
    return {'now': datetime.now()}

# Simple in-memory cache for billing API
billing_cache = {}  # (month, year): (timestamp, data)
CACHE_TTL = 60  # seconds

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/instructors')
def instructors():
    sheet_name = os.getenv("INSTRUCTORS_SHEET_NAME")
    headers, instructors = get_sheet_data(sheet_name)
    
    # Ensure the status field is properly formatted and add sheet_row for persistent identification
    for idx, instructor in enumerate(instructors):
        if 'פעיל' in instructor:
            instructor['פעיל'] = instructor['פעיל'].strip() if instructor['פעיל'] else ''
        instructor['sheet_row'] = idx + 2  # +2 because 1 for header, and enumerate starts at 0
    
    # Sort instructors: active first, then inactive (with 'לא פעיל' status)
    sorted_instructors = sorted(
        instructors,
        key=lambda x: 1 if x.get('פעיל') == 'לא פעיל' else 0
    )
    
    return render_template('instructors.html', headers=headers, instructors=sorted_instructors)

@app.route('/update_instructor', methods=['POST'])
def update_instructor_route():
    data = request.json
    sheet_row = data.get('sheet_row')  # This is the persistent row index in the Google Sheet
    instructor_data = data.get('data')  # This is the updated instructor data
    
    sheet_name = os.getenv("INSTRUCTORS_SHEET_NAME")
    
    try:
        # Get headers from first row
        headers = ['שם', 'טלפון', 'מייל', 'התמחויות', 'הערות', 'פעיל']
        
        # Create ordered list of values based on header order
        values = [
            instructor_data.get('שם', ''),
            instructor_data.get('טלפון', ''),
            instructor_data.get('מייל', ''),
            instructor_data.get('התמחויות', ''),
            instructor_data.get('הערות', ''),
            instructor_data.get('פעיל', '')
        ]

        # Create cell updates
        updates = {}
        for idx, value in enumerate(values, start=1):
            updates[idx] = value
        
        # Send a single batch update to the sheet
        if updates:
            update_instructor(sheet_name, sheet_row, updates)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating instructor: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/add_instructor', methods=['POST'])
def add_instructor_route():
    data = request.json
    instructor_data = data.get('data')
    sheet_name = os.getenv("INSTRUCTORS_SHEET_NAME")
    try:
        # Get headers to ensure order
        headers = ['שם', 'טלפון', 'מייל', 'התמחויות', 'הערות', 'פעיל']
        values = [
            instructor_data.get('שם', ''),
            instructor_data.get('טלפון', ''),
            instructor_data.get('מייל', ''),
            instructor_data.get('התמחויות', ''),
            instructor_data.get('הערות', ''),
            instructor_data.get('פעיל', '')
        ]
        add_instructor(sheet_name, values)
        # Find the new row index (header + all records + 1)
        _, instructors = get_sheet_data(sheet_name)
        sheet_row = len(instructors) + 1  # +1 for header row
        return jsonify({'success': True, 'sheet_row': sheet_row})
    except Exception as e:
        print(f"Error adding instructor: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clients/private')
def clients_private():
    sheet_name = os.getenv("clients_private_SHEET_NAME")
    headers, clients = get_sheet_data(sheet_name)
    
    # Add sheet_row for persistent identification
    for idx, client in enumerate(clients):
        client['sheet_row'] = idx + 2  # +2 because 1 for header, and enumerate starts at 0
        if 'פעיל' in client:
            client['פעיל'] = client['פעיל'].strip() if client['פעיל'] else ''
    
    return render_template('clients_private.html', headers=headers, clients=clients)

@app.route('/add_private_client', methods=['POST'])
def add_private_client_route():
    data = request.json
    client_data = data.get('data')
    sheet_name = os.getenv("clients_private_SHEET_NAME")
    try:
        # Get headers to ensure order
        headers = ['שם', 'טלפון', 'מייל', 'צורך מיוחד', 'הערות', 'פעיל']
        values = [
            client_data.get('שם', ''),
            client_data.get('טלפון', ''),
            client_data.get('מייל', ''),
            client_data.get('צורך מיוחד', ''),
            client_data.get('הערות', ''),
            client_data.get('פעיל', '')
        ]
        add_instructor(sheet_name, values)  # Reusing the same function as it has the same logic
        # Find the new row index (header + all records + 1)
        _, clients = get_sheet_data(sheet_name)
        sheet_row = len(clients) + 1  # +1 for header row
        return jsonify({'success': True, 'sheet_row': sheet_row})
    except Exception as e:
        print(f"Error adding private client: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/update_private_client', methods=['POST'])
def update_private_client_route():
    print("\n=== Starting update_private_client_route ===")
    try:
        # Log incoming request data
        print("Raw request data:", request.data)
        data = request.get_json()
        print("Parsed JSON data:", data)
        
        if not data:
            error_msg = 'No data provided in request'
            print(f"Error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        sheet_row = data.get('sheet_row')
        client_data = data.get('data', {})
        print(f"Sheet row: {sheet_row}")
        print("Client data:", client_data)
        
        if not sheet_row:
            error_msg = 'Missing sheet_row in request data'
            print(f"Error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        sheet_name = os.getenv("clients_private_SHEET_NAME")
        print(f"Using sheet name: {sheet_name}")
        
        if not sheet_name:
            error_msg = 'Sheet name not configured in environment variables'
            print(f"Error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
        
        # Define the expected columns in order
        headers = ['שם', 'טלפון', 'מייל', 'צורך מיוחד', 'הערות', 'פעיל']
        print("Headers:", headers)
        
        # Create updates dictionary with column indices (1-based) and values
        updates = {}
        for idx, header in enumerate(headers, start=1):
            # Use get with default empty string to handle missing keys
            value = client_data.get(header, '')
            updates[idx] = value
            print(f"Column {idx} ({header}): {value}")
        
        print("Updates to be made:", updates)
        
        # Update the row in the sheet
        from utils.google_sheets import update_instructor
        print("Calling update_instructor...")
        update_instructor(sheet_name, sheet_row, updates)
        print("Successfully updated instructor data")
        
        response = {'success': True}
        print("Returning success response:", response)
        return jsonify(response)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Error updating private client: {str(e)}"
        print("\n" + "="*50)
        print("ERROR DETAILS:")
        print(error_msg)
        print("\nStack trace:")
        print(error_details)
        print("="*50 + "\n")
        
        return jsonify({
            'success': False, 
            'error': 'An error occurred while updating the client. Please try again.',
            'details': str(e)
        }), 500

@app.route('/clients/institutional')
def clients_institutional():
    sheet_name = os.getenv("clients_institutional_SHEET_NAME")
    headers, clients = get_sheet_data(sheet_name)
    
    # Add sheet_row to each client
    for i, client in enumerate(clients, start=2):  # Start from 2 because of 1-based indexing and header row
        client['sheet_row'] = i
    
    # Arrange headers in the desired order
    desired_headers = ['גוף', 'איש קשר', 'טלפון', 'מייל', 'הערות']
    # Filter only headers that exist in the worksheet and are in our desired headers
    headers = [h for h in desired_headers if h in headers and h in clients[0].keys()] if clients else desired_headers
    
    return render_template('clients_institutional.html', headers=headers, clients=clients)

@app.route('/add_institutional_client', methods=['POST'])
def add_institutional_client_route():
    try:
        data = request.get_json()
        print("Add client - Received data:", data)  # Debug log
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'})
        
        # The data comes directly in the root of the JSON
        client_data = data
        
        # Get the sheet name from environment variable
        sheet_name = os.getenv("clients_institutional_SHEET_NAME")
        if not sheet_name:
            return jsonify({'success': False, 'error': 'Sheet name not configured'})
        
        # Prepare the row data in the correct order
        row_data = [
            client_data.get('ארגון', ''),  # Organization
            client_data.get('איש קשר', ''),  # Contact person
            client_data.get('טלפון', ''),  # Phone
            client_data.get('מייל', ''),  # Email
            client_data.get('הערות', ''),  # Notes
            client_data.get('פעיל', '')   # Active status (empty string means active)
        ]
        
        print("Add client - Row data to append:", row_data)  # Debug log
        
        # Add the new client to the sheet
        result = append_row(sheet_name, row_data)
        print("Add client - Append result:", result)  # Debug log
        
        if result:
            return jsonify({'success': True, 'message': 'Client added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to add client'})
    except Exception as e:
        print(f"Error adding institutional client: {e}")
        return jsonify({'success': False, 'error': str(e)})
@app.route('/update_institutional_client', methods=['POST'])
def update_institutional_client_route():
    try:
        data = request.get_json()
        print("Update client - Received data:", data)  # Debug log
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'})
            
        sheet_row = data.get('sheet_row')
        client_data = data  # The data comes directly in the root of the JSON
        
        if not sheet_row:
            return jsonify({'success': False, 'error': 'Missing sheet_row parameter'})
        
        # Get the sheet name from environment variable
        sheet_name = os.getenv("clients_institutional_SHEET_NAME")
        if not sheet_name:
            return jsonify({'success': False, 'error': 'Sheet name not configured'})
        
        # Map the fields to update with their column letters
        updates = {}
        field_mapping = {
            'A': client_data.get('ארגון'),  # Column A: Organization
            'B': client_data.get('איש קשר'),  # Column B: Contact Person
            'C': client_data.get('טלפון'),  # Column C: Phone
            'D': client_data.get('מייל'),  # Column D: Email
            'E': client_data.get('הערות'),  # Column E: Notes
            'F': client_data.get('פעיל')    # Column F: Active status
        }
        
        # Only include non-None values
        updates = {col: val for col, val in field_mapping.items() if val is not None}
        
        if not updates:
            return jsonify({'success': False, 'error': 'No valid fields to update'})
            
        print(f"Update client - Updating row {sheet_row} with:", updates)  # Debug log
        
        # Update the client in the sheet
        result = update_row(sheet_name, sheet_row, updates)
        print("Update client - Result:", result)  # Debug log
        
        if result:
            return jsonify({'success': True, 'message': 'Client updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update client'})
    except Exception as e:
        print(f"Error updating institutional client: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/payments')
def payments():
    # Get current month and year
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # Get selected month and year from query parameters
    try:
        selected_month = int(request.args.get('month', current_month))
        selected_year = int(request.args.get('year', current_year))
    except (ValueError, TypeError):
        selected_month = current_month
        selected_year = current_year
    
    # Generate years for the dropdown (previous, current, next year)
    years = [current_year-1, current_year, current_year+1]
    
    # Get payment data for the selected month/year
    payment_data = get_payment_data(selected_month, selected_year)
    
    # Define Hebrew months for the dropdown
    hebrew_months = [
        (1, 'ינואר'), (2, 'פברואר'), (3, 'מרץ'), (4, 'אפריל'),
        (5, 'מאי'), (6, 'יוני'), (7, 'יולי'), (8, 'אוגוסט'),
        (9, 'ספטמבר'), (10, 'אוקטובר'), (11, 'נובמבר'), (12, 'דצמבר')
    ]
    
    return render_template(
        'payments.html',
        headers=['מדריך', 'סהכ שעות', 'לפי לקוח', 'לקוח', 'שכר שעה', 'סיכום'],
        records=payment_data.get('records', []),
        months=hebrew_months,
        years=years,
        selected_month=selected_month,
        selected_year=selected_year,
        total_hours=payment_data.get('total_hours', 0),
        total_payment=payment_data.get('total_payment', 0)
    )

def get_payment_data(month, year):
    """Fetch and process payment data for a specific month and year."""
    try:
        # Get calendar service
        service = get_calendar_service()
        if not service:
            return {'records': [], 'total_hours': 0, 'total_payment': 0}
        
        # Calculate date range for the month
        start_date = datetime(year, month, 1).isoformat() + 'Z'  # 'Z' indicates UTC time
        if month == 12:
            end_date = datetime(year + 1, 1, 1).isoformat() + 'Z'
        else:
            end_date = datetime(year, month + 1, 1).isoformat() + 'Z'
        
        # Fetch events from calendar
        events_result = service.events().list(
            calendarId=os.getenv('CALENDAR_ID'),
            timeMin=start_date,
            timeMax=end_date,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Get valid clients for filtering
        valid_clients = get_client_names_from_sheets()
        
        # Filter events by valid client names
        filtered_events = []
        for event in events:
            title = event.get('summary', '').strip()
            # Find matching client name anywhere in the title
            for client in valid_clients:
                if client in title:
                    event['matched_client'] = client  # Store matched client name
                    filtered_events.append(event)
                    break
        
        # Process filtered events into payment data
        instructor_data = {}
        instructors_map = create_instructors_map()
        valid_instructors = set(instructors_map.values())  # Get set of valid instructor names
        
        for event in filtered_events:
            # Skip events without an organizer
            if 'organizer' not in event or 'email' not in event['organizer']:
                continue
                
            # Get instructor name from email
            organizer_email = event['organizer']['email']
            username = organizer_email.split('@')[0]
            instructor_name = instructors_map.get(username, username)
            
            # Skip if instructor not in valid instructors
            if instructor_name not in valid_instructors:
                continue
            
            # Calculate event duration in hours
            start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
            end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date'))
            
            if not start or not end:
                continue
                
            try:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                duration_hours = (end_dt - start_dt).total_seconds() / 3600
            except (ValueError, TypeError):
                continue
            
            # Use the pre-matched client name from the filter
            client_name = event.get('matched_client', 'Unknown Client')
            
            # Initialize instructor data if not exists
            if instructor_name not in instructor_data:
                # Try to get the saved hourly wage, or use default (200)
                saved_hourly_wage = get_hourly_wage(instructor_name, month, year) or 200
                instructor_data[instructor_name] = {
                    'total_hours': 0,
                    'by_client': {},
                    'hourly_rate': saved_hourly_wage,  # Use saved rate or default
                    'total_payment': 0
                }
            
            # Update instructor data
            instructor = instructor_data[instructor_name]
            instructor['total_hours'] += duration_hours
            
            # Track hours by client
            if client_name not in instructor['by_client']:
                instructor['by_client'][client_name] = 0
            instructor['by_client'][client_name] += duration_hours
        
        # Calculate total payment for each instructor
        for instructor in instructor_data.values():
            instructor['total_payment'] = instructor['total_hours'] * instructor['hourly_rate']
        
        # Convert to records for display
        records = []
        total_hours = 0
        total_payment = 0
        
        for instructor_name, data in instructor_data.items():
            # Format client breakdown - show only numeric hours without 'שעות'
            client_hours = [f"{hours:.1f}" for client, hours in data['by_client'].items()]
            client_names = list(data['by_client'].keys())
            
            # For HTML display, use both newlines and br tags to support both spreadsheet export and HTML display
            records.append({
                'instructor': instructor_name,
                'total_hours': f"{data['total_hours']:.1f}",
                'by_client': '\n'.join([f"{h}<br>" for h in client_hours]),  # Add <br> tags for HTML display
                'client': '\n'.join([f"{c}<br>" for c in client_names]),  # Add <br> tags for HTML display
                'hourly_rate': f"{data['hourly_rate']:,.2f}",
                'total_payment': f"{data['total_payment']:,.2f}"
            })
            
            total_hours += data['total_hours']
            total_payment += data['total_payment']
        
        return {
            'records': records,
            'total_hours': total_hours,
            'total_payment': total_payment
        }
        
    except Exception as e:
        print(f"Error getting payment data: {e}")
        return {'records': [], 'total_hours': 0, 'total_payment': 0}

# Define Hebrew months for the billing dropdown
HEBREW_MONTHS = [
    {'value': '1', 'display': 'ינואר'},
    {'value': '2', 'display': 'פברואר'},
    {'value': '3', 'display': 'מרץ'},
    {'value': '4', 'display': 'אפריל'},
    {'value': '5', 'display': 'מאי'},
    {'value': '6', 'display': 'יוני'},
    {'value': '7', 'display': 'יולי'},
    {'value': '8', 'display': 'אוגוסט'},
    {'value': '9', 'display': 'ספטמבר'},
    {'value': '10', 'display': 'אוקטובר'},
    {'value': '11', 'display': 'נובמבר'},
    {'value': '12', 'display': 'דצמבר'}
]

@app.route('/billing')
def billing():
    # Get current month and year
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # Get selected month and year from query parameters
    try:
        selected_month = int(request.args.get('month', current_month))
        selected_year = int(request.args.get('year', current_year))
    except (ValueError, TypeError):
        selected_month = current_month
        selected_year = current_year
    
    # Generate years for the dropdown (previous, current, next year)
    years = [current_year - 1, current_year, current_year + 1]
    
    # Empty records - will be populated by client-side JavaScript
    billing_records = []
    
    # Define headers
    desired_headers = ['לקוח', 'סהכ שעות', 'לפי מדריך', 'מדריך', 'תמחור שעה', 'הנחה %', 'סיכום']

    return render_template('billing.html',
                         headers=desired_headers,
                         records=billing_records,
                         hebrew_months=HEBREW_MONTHS,
                         current_month=current_month,
                         current_year=current_year,
                         selected_month=selected_month,
                         selected_year=selected_year,
                         years=years)

def get_client_names_from_sheets():
    """Fetch client names from both private and institutional clients sheets."""
    from utils.google_sheets import get_sheet_data
    
    try:
        # Get private clients
        private_clients_sheet = os.getenv("clients_private_SHEET_NAME", "לקוחות פרטיים")
        _, private_clients = get_sheet_data(private_clients_sheet)
        private_client_names = {client.get('שם', '').strip() for client in private_clients if client.get('שם').strip()}
        
        # Get institutional clients
        institutional_clients_sheet = os.getenv("clients_institutional_SHEET_NAME", "לקוחות מוסדיים")
        _, institutional_clients = get_sheet_data(institutional_clients_sheet)
        institutional_client_names = {client.get('גוף', '').strip() for client in institutional_clients if client.get('גוף').strip()}
        
        # Combine all client names
        all_client_names = private_client_names.union(institutional_client_names)
        print(f"DEBUG: Found {len(all_client_names)} unique client names in sheets")
        return all_client_names
        
    except Exception as e:
        print(f"ERROR fetching client names: {str(e)}")
        import traceback
        traceback.print_exc()
        return set()

def create_instructors_map():
    """Create a mapping of email usernames to full instructor names"""
    try:
        # Get the sheet name from environment variables or use a default
        sheet_name = os.getenv("INSTRUCTORS_SHEET_NAME", "מדריכים")
        instructors = fetch_instructors(sheet_name)
        email_to_name = {}
        for instructor in instructors:
            email = instructor.get('מייל', '').strip()
            if '@' in email:
                username = email.split('@')[0]
                email_to_name[username] = instructor.get('שם', username)
        return email_to_name
    except Exception as e:
        print(f"Error creating instructors map: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

@app.route('/api/billing')
def get_billing_data():
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    cache_key = (month, year)
    now = time()
    # Serve from cache if fresh
    if cache_key in billing_cache:
        ts, data = billing_cache[cache_key]
        if now - ts < CACHE_TTL:
            print("Serving billing data from cache")
            return jsonify(data)
    print("DEBUG: /api/billing endpoint called")
    try:
        # Get all valid client names from Google Sheets
        valid_client_names = get_client_names_from_sheets()
        print(f"DEBUG: Valid client names: {valid_client_names}")
        
        # Create instructor mapping
        instructors_map = create_instructors_map()
        
        # Calculate the date range for the selected month (in local timezone)
        local_tz = pytz.timezone('Asia/Jerusalem')
        start_date = local_tz.localize(datetime(year, month, 1))
        
        if month == 12:
            end_date = local_tz.localize(datetime(year + 1, 1, 1))
        else:
            end_date = local_tz.localize(datetime(year, month + 1, 1))
        
        print(f"DEBUG: Date range (local time): {start_date} to {end_date}")
        
        # Fetch events from Google Calendar
        events = fetch_events_from_calendar(start_date, end_date)
        print(f"DEBUG: Found {len(events)} events before filtering")
        
        # Fetch rates and discounts for this month/year
        rates_discounts = {}  # {client: {"תמחור שעה": value, "הנחה %": value}}
        try:
            gc = get_gspread_client()
            spreadsheet_id = os.getenv('billing_SPREADSHEET_ID')
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet('תעריפים והנחות')
            records = worksheet.get_all_records()
            for record in records:
                if str(record.get('חודש', '')).strip() == str(month) and str(record.get('שנה', '')).strip() == str(year):
                    client = record['לקוח']
                    typ = record['סוג']
                    value = float(record['ערך']) if record['ערך'] else 0
                    if client not in rates_discounts:
                        rates_discounts[client] = {}
                    rates_discounts[client][typ] = value
        except Exception as e:
            print(f"Error fetching rates/discounts: {e}")
        
        # Process events to group by client and calculate hours
        client_data = {}
        filtered_out_count = 0
        
        for event in events:
            try:
                # Get the event summary/title
                event_summary = event.get('summary', '').strip()
                if not event_summary:
                    print(f"DEBUG: Skipping event with no summary")
                    filtered_out_count += 1
                    continue
                
                # Find if any client name is present in the event title
                client_name = None
                for name in valid_client_names:
                    if name and name in event_summary:
                        client_name = name
                        break
                
                # Skip events that don't contain any valid client name
                if not client_name:
                    print(f"DEBUG: Skipping event - no matching client name found in: {event_summary}")
                    filtered_out_count += 1
                    continue
                
                print(f"DEBUG: Matched client '{client_name}' in event: {event_summary}")
                
                # Get organizer's email and map to instructor name
                organizer_email = event.get('organizer', {}).get('email', '')
                organizer_username = organizer_email.split('@')[0] if '@' in organizer_email else ''
                instructor_name = instructors_map.get(organizer_username, organizer_username)
                
                # Calculate event duration in hours
                start = parse_iso_datetime(event['start'].get('dateTime', event['start'].get('date')))
                end = parse_iso_datetime(event['end'].get('dateTime', event['end'].get('date')))
                
                if not start or not end:
                    print(f"DEBUG: Skipping event with invalid dates: {event_summary}")
                    filtered_out_count += 1
                    continue
                
                # Convert to local timezone for consistent calculation
                if start.tzinfo is None:
                    start = local_tz.localize(start)
                if end.tzinfo is None:
                    end = local_tz.localize(end)
                
                duration_hours = (end - start).total_seconds() / 3600
                print(f"DEBUG: Processing event: {event_summary}, Duration: {duration_hours:.2f} hours, Instructor: {instructor_name}")
                
                # Initialize client data if not exists
                if client_name not in client_data:
                    client_data[client_name] = {
                        'total_hours': 0,
                        'instructors': {}
                    }
                
                # Update client's total hours
                client_data[client_name]['total_hours'] += duration_hours
                
                # Update instructor hours
                if instructor_name in client_data[client_name]['instructors']:
                    client_data[client_name]['instructors'][instructor_name] += duration_hours
                else:
                    client_data[client_name]['instructors'][instructor_name] = duration_hours
                    
            except Exception as e:
                print(f"ERROR processing event: {str(e)}")
                import traceback
                traceback.print_exc()
                filtered_out_count += 1
                continue
        
        print(f"DEBUG: Processed {len(events)} events, filtered out {filtered_out_count} events")
        print(f"DEBUG: Client data: {client_data}")
        
        # Convert to the format expected by the frontend
        billing_data = []
        for client, data in client_data.items():
            # Create a dictionary with all required keys in the correct order
            record = {}
            
            # Format instructor hours for display
            instructor_hours = []
            instructor_names = []
            
            for name, hours in data['instructors'].items():
                instructor_hours.append(f"{hours:.1f}")
                instructor_names.append(name)
            
            # Map the data to the correct columns
            # Format values for display
            record['לקוח'] = client  # Client name
            record['סהכ שעות'] = round(data['total_hours'], 2)  # Total hours
            record['לפי מדריך'] = '\n'.join(instructor_hours)  # Hours by instructor
            record['מדריך'] = '\n'.join(instructor_names)  # Instructor names
            # Use rates/discounts if available, else default
            rate = 350
            discount = 0
            if client in rates_discounts:
                if 'תמחור שעה' in rates_discounts[client]:
                    rate = rates_discounts[client]['תמחור שעה']
                if 'הנחה %' in rates_discounts[client]:
                    discount = rates_discounts[client]['הנחה %']
            record['תמחור שעה'] = rate
            record['הנחה %'] = discount
            # Calculate total based on hours * rate * (1 - discount/100)
            record['סיכום'] = round(data['total_hours'] * rate * (1 - discount / 100), 2)
            
            billing_data.append(record)
            
            # Debug output
            print(f"DEBUG: Added record - Client: {client}, Hours: {data['total_hours']}, Instructors: {instructor_names}, Rate: {rate}, Discount: {discount}")
        
        # Sort clients alphabetically
        billing_data.sort(key=lambda x: x['לקוח'])
        
        # Prepare response
        response_data = {
            'status': 'success',
            'data': billing_data
        }
        # Update cache
        billing_cache[cache_key] = (now, response_data)
        # Debug log the response
        print("DEBUG: Sending response:")
        print(f"Status: success")
        print(f"Number of records: {len(billing_data)}")
        if billing_data:
            print("First record sample:", {k: billing_data[0][k] for k in billing_data[0].keys()})
        return jsonify(response_data)
    except Exception as e:
        print(f"ERROR in get_billing_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def parse_iso_datetime(dt_str):
    """Parse ISO datetime string to datetime object"""
    if not dt_str:
        return None
    try:
        if 'T' in dt_str:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            return datetime.strptime(dt_str, '%Y-%m-%d')
    except (ValueError, TypeError) as e:
        print(f"Error parsing datetime {dt_str}: {str(e)}")
        return None

def get_calendar_service():
    """Get an authorized Google Calendar API service instance using service account."""
    from google.oauth2 import service_account
    
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
    
    if not SERVICE_ACCOUNT_FILE or not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"Error: Service account file not found at {SERVICE_ACCOUNT_FILE}")
        return None
    
    try:
        # Create credentials using the service account file
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, 
            scopes=SCOPES
        )
        
        # Create the service
        service = build('calendar', 'v3', credentials=creds)
        print("Successfully created Google Calendar service")
        return service
        
    except Exception as e:
        print(f"Error creating calendar service: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def fetch_events_from_calendar(start_date, end_date):
    """Fetch events from Google Calendar for the given date range"""
    print("\n=== Starting fetch_events_from_calendar ===")
    print(f"Start date: {start_date}, End date: {end_date}")
    
    try:
        # Get the Google Calendar service
        print("Getting calendar service...")
        service = get_calendar_service()
        
        if not service:
            print("❌ Failed to get calendar service")
            return []
            
        print("✅ Successfully got calendar service")
        
        # Get the calendar ID from environment variables
        calendar_id = os.getenv('CALENDAR_ID', 'primary')
        print(f"Using calendar ID: {calendar_id}")
        
        # Format dates for the API (in UTC, without timezone offset)
        time_min = start_date.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        time_max = end_date.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        print(f"\n🔍 Fetching events from {time_min} to {time_max}")
        
        # Prepare the API request
        request = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=1000
        )
        
        print("\n📡 Sending API request...")
        print(f"Request URL: {request.uri}")
        print(f"Request method: {request.method}")
        print(f"Request headers: {request.headers}")
        
        # Execute the request
        events_result = request.execute()
        
        print("\n✅ API Response received")
        print(f"Response keys: {list(events_result.keys())}")
        
        items = events_result.get('items', [])
        print(f"\n📅 Found {len(items)} events in calendar {calendar_id}")
        
        # Debug: Print event details
        if not items:
            print("No events found in the specified date range")
        else:
            print("\n=== First 3 events ===")
            for i, item in enumerate(items[:3]):
                summary = item.get('summary', 'No title')
                start = item.get('start', {})
                end = item.get('end', {})
                print(f"\nEvent {i+1}:")
                print(f"  Summary: {summary}")
                print(f"  Start: {start.get('dateTime', start.get('date', 'No start date'))}")
                print(f"  End: {end.get('dateTime', end.get('date', 'No end date'))}")
                print(f"  Status: {item.get('status', 'No status')}")
        
        print("\n=== End of fetch_events_from_calendar ===\n")
        return items
        
    except Exception as e:
        print("\n❌ Error in fetch_events_from_calendar:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nStack trace:")
        import traceback
        traceback.print_exc()
        print("\n=== End of error ===\n")
        return []

@app.route('/calendar')
def calendar_page():
    # Get month/year from query params or use current
    now = datetime.now(pytz.timezone('Asia/Jerusalem'))
    month = int(request.args.get('month', now.month))
    year = int(request.args.get('year', now.year))

    # Google Calendar API setup
    SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
    CALENDAR_ID = os.getenv('CALENDAR_ID')
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    # Get all clients for filtering (both private and institutional)
    # Get private clients
    private_clients_sheet = os.getenv("clients_private_SHEET_NAME")
    _, private_clients = get_sheet_data(private_clients_sheet)
    private_client_names = [client.get('שם', '').strip() for client in private_clients if client.get('שם')]
    
    # Get institutional clients
    institutional_clients_sheet = os.getenv("clients_institutional_SHEET_NAME")
    _, institutional_clients = get_sheet_data(institutional_clients_sheet)
    institutional_client_names = [client.get('גוף', '').strip() for client in institutional_clients if client.get('גוף')]
    
    # Combine all client names
    all_client_names = private_client_names + institutional_client_names
    
    # Get instructors data for name mapping
    instructors_sheet = os.getenv("INSTRUCTORS_SHEET_NAME")
    _, instructors = get_sheet_data(instructors_sheet)
    
    # Create a mapping of instructor emails to their names
    email_to_name = {}
    for instructor in instructors:
        if 'מייל' in instructor and 'שם' in instructor:
            email = instructor['מייל'].strip().lower()
            name = instructor['שם'].strip()
            if email and name:
                email_to_name[email] = name
    
    credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)

    # Get start/end of month
    start_date = datetime(year, month, 1, tzinfo=pytz.timezone('Asia/Jerusalem'))
    if month == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=pytz.timezone('Asia/Jerusalem'))
    else:
        end_date = datetime(year, month + 1, 1, tzinfo=pytz.timezone('Asia/Jerusalem'))

    # Fetch events
    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_date.isoformat(),
        timeMax=end_date.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    # Group events by day
    events_by_day = {}
    for event in events_result.get('items', []):
        title = event.get('summary', '')
        
        # Find the client name in the title (if any)
        client_in_title = None
        for client_name in all_client_names:
            if client_name and client_name in title:
                client_in_title = client_name
                break
                
        # Skip events that don't have any client name (private or institutional) in the title
        if not client_in_title:
            continue
            
        start = event['start'].get('dateTime', event['start'].get('date'))
        try:
            dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        except Exception:
            dt = datetime.strptime(start, "%Y-%m-%d")
        day = dt.day
        time_str = dt.strftime('%H:%M') if 'T' in start else ''
        
        if day not in events_by_day:
            events_by_day[day] = []
            
        # Store both the display title and full event data
        # Ensure all values are JSON serializable
        
        # Get creator's email if available
        creator_email = ''
        creator_name = 'לא צוין'
        if 'creator' in event and 'email' in event['creator']:
            creator_email = event['creator']['email']
            # Get instructor name from email if available
            creator_name = email_to_name.get(creator_email.lower(), creator_email)
        
        # Get end time for duration calculation
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        event_data = {
            'time': time_str, 
            'title': client_in_title or 'אין כותרת',  # Ensure title is never None
            'organizer': creator_name,  # Use instructor's name instead of email
            'full_event': {  # Full event data for the popup
                'title': title or 'אין כותרת',
                'start': start,
                'end': end,  # Add end time
                'creator_email': creator_email,  # Keep email in full event data
                'creator_name': creator_name,    # Add name to full event data
                'description': event.get('description') or '',
                'location': event.get('location') or 'לא צוין מיקום',
                'attendees': [a.get('email', '') for a in event.get('attendees', []) if a and 'email' in a],
                'client_name': client_in_title or 'לא צוין'
            }
        }
        events_by_day[day].append(event_data)

    # Hebrew day names (RTL order)
    hebrew_days = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    hebrew_months = [
        "", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
        "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
    ]

    # Days in month and first day of the week (0 = Monday, 6 = Sunday)
    first_day_of_week, days_in_month = pycalendar.monthrange(year, month)
    
    # Convert to Sunday = 0, Saturday = 6 format by adding 1 and taking modulo 7
    # This aligns with hebrew_days array which starts with Sunday
    first_day_sunday_based = (first_day_of_week + 1) % 7
    
    # Generate calendar offset days for proper alignment
    offset_days = first_day_sunday_based
    
    # Hebrew months list with 1-based indexing (index 0 is empty)
    hebrew_months_list = [
        "", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
        "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
    ]
    
    return render_template(
        'calendar.html',
        year=year,
        month=month,
        month_name=hebrew_months[month],
        hebrew_days=hebrew_days,
        days_in_month=days_in_month,
        offset_days=offset_days,
        hebrew_months=hebrew_months_list,
        events_by_day=events_by_day,
        today=date.today()
    )

@app.route('/api/clients/<unique_id>', methods=['GET'])
def get_client(unique_id):
    sheet_name = os.getenv("clients_private_SHEET_NAME")
    _, clients = get_sheet_data(sheet_name)
    
    # Find client by unique_id
    client = next((c for c in clients if c.get('unique_id') == unique_id), None)
    if not client:
        return jsonify({'error': 'Client not found'}), 404
        
    return jsonify(client)

@app.route('/api/clients/<unique_id>', methods=['PUT'])
def update_client(unique_id):
    sheet_name = os.getenv("clients_private_SHEET_NAME")
    data = request.json
    
    try:
        # Get current data
        headers, clients = get_sheet_data(sheet_name)
        
        # Find client row index
        client_index = next((idx for idx, c in enumerate(clients) 
                           if c.get('unique_id') == unique_id), None)
        
        if client_index is None:
            return jsonify({'error': 'Client not found'}), 404
            
        # Update sheet row (add 2 for header row and 0-based index)
        sheet_row = client_index + 2
        
        # Create updates dictionary
        updates = {
            idx + 1: data.get(header, '')
            for idx, header in enumerate(headers)
        }
        
        # Update the sheet
        update_instructor(sheet_name, sheet_row, updates)
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error updating client: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export_billing', methods=['POST'])
def export_billing_to_sheets():
    try:
        data = request.json
        month = int(data.get('month'))
        year = int(data.get('year'))
        billing_data = data.get('data', [])
        
        if not billing_data:
            return jsonify({'success': False, 'error': 'No data to export'}), 400
        
        # Get Hebrew month name
        hebrew_months = [
            'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
            'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'
        ]
        worksheet_name = f"{hebrew_months[month-1]} {year}"
        
        # Get Google Sheets client
        gc = get_gspread_client()
        spreadsheet_id = os.getenv('billing_SPREADSHEET_ID')
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        # Define headers in the specified RTL order (excluding 'מספר' column)
        headers = [
            'סיכום', 'הנחה %', 'תמחור שעה', 'מדריך', 'לפי מדריך',
            'סהכ שעות', 'לקוח'
        ]
        
        # Try to get the worksheet, create if it doesn't exist
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            worksheet_fresh = False
        except gspread.exceptions.WorksheetNotFound:
            # Create a new worksheet with headers and formatting (only 7 columns A-G)
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=7)
            worksheet.append_row(headers)
            
            # Set column widths (in pixels, approximate values for good fit)
            # Column widths: A: 80, B: 80, C: 100, D: 200, E: 150, F: 100, G: 200
            column_widths = [
                {'startColumnIndex': 0, 'endColumnIndex': 1, 'pixelSize': 150},   # Column A
                {'startColumnIndex': 1, 'endColumnIndex': 2, 'pixelSize': 80},   # Column B
                {'startColumnIndex': 2, 'endColumnIndex': 3, 'pixelSize': 100},  # Column C
                {'startColumnIndex': 3, 'endColumnIndex': 4, 'pixelSize': 200},  # Column D
                {'startColumnIndex': 4, 'endColumnIndex': 5, 'pixelSize': 150},  # Column E
                {'startColumnIndex': 5, 'endColumnIndex': 6, 'pixelSize': 100},  # Column F
                {'startColumnIndex': 6, 'endColumnIndex': 7, 'pixelSize': 200}   # Column G
            ]
            
            # Apply column widths in a batch update
            body = {
                'requests': [{
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': worksheet.id,
                            'dimension': 'COLUMNS',
                            'startIndex': width['startColumnIndex'],
                            'endIndex': width['endColumnIndex']
                        },
                        'properties': {
                            'pixelSize': width['pixelSize']
                        },
                        'fields': 'pixelSize'
                    }
                } for width in column_widths]
            }
            
            try:
                spreadsheet.batch_update(body)
            except Exception as e:
                print(f"Warning: Could not set column widths: {e}")
                
            worksheet_fresh = True
        
        # For existing worksheets, update headers if needed
        if not worksheet_fresh:
            # Get existing data to check headers
            existing_data = worksheet.get_all_values()
            existing_headers = existing_data[0] if existing_data else []
            
            # Update headers if they don't match
            if not existing_headers or len(existing_headers) < len(headers):
                worksheet.update('A1', [headers])
        
        # Apply header formatting (for both new and existing worksheets)
        header_format = {
            'textFormat': {
                'bold': True,
                'foregroundColor': {'red': 0.0, 'green': 0.0, 'blue': 1.0}  # Blue color
            },
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},  # Light gray
            'horizontalAlignment': 'CENTER',
            'verticalAlignment': 'MIDDLE'
        }
        worksheet.format('A1:H1', header_format)
        
        # Clear existing data (except headers) if there are any rows
        try:
            if worksheet.row_count > 1:
                # Delete all rows starting from row 2 to the end
                worksheet.delete_rows(2, worksheet.row_count)
        except Exception as e:
            print(f"Warning: Could not clear existing rows: {e}")
            # If clearing fails, try to clear the worksheet another way
            try:
                worksheet.clear()
                # Re-add headers after clearing
                worksheet.append_row(headers)
                worksheet.format('A1:H1', header_format)
            except Exception as e2:
                print(f"Error clearing worksheet: {e2}")
                # If we can't clear, continue and let the append update the data
        
        # Prepare data for export
        rows = []
        for item in billing_data:
            # Helper function to safely get and format values
            def get_value(key, default='', is_percent=False, keep_newlines=False):
                # The values are already processed on the client side, so we can use them as is
                value = item.get(key, default)
                if value is None:
                    return default
                if is_percent:
                    # For percentages, ensure we return a number without the % sign
                    if isinstance(value, str):
                        return str(value).replace('%', '')
                    return str(value)
                if isinstance(value, (int, float)):
                    return value
                if not keep_newlines:
                    return str(value).replace('\n', ' ')
                return str(value)
            
            # Prepare row data in the specified RTL order (excluding 'מספר' column)
            # Get values exactly as they appear in the table
            def format_number(value):
                if value is None:
                    return ''
                return str(value).replace(',', '')  # Remove any thousands separators
            
            # Get all values
            summary = format_number(get_value('סיכום'))
            discount = format_number(get_value('הנחה %', is_percent=True))
            rate = format_number(get_value('תמחור שעה'))
            by_instructor = get_value('לפי מדריך', keep_newlines=True)
            instructor = get_value('מדריך', keep_newlines=True)
            total_hours = format_number(get_value('סהכ שעות'))
            client = get_value('לקוח')
            
            # Create the row with columns in the correct order and swapped columns D and E
            # Prefix numeric values with a single quote to force text format in Google Sheets
            row = [
                f"'{summary}" if summary.replace('.', '', 1).isdigit() else summary,  # A: סיכום
                discount,         # B: הנחה %
                rate,             # C: תמחור שעה
                by_instructor,    # D: לפי מדריך (swapped with E)
                instructor,       # E: מדריך (swapped with D)
                total_hours,      # F: סהכ שעות
                client            # G: לקוח
            ]
            rows.append(row)
        
        # Add data to worksheet with proper formatting
        if rows:
            # First, clear existing content (except headers)
            if len(worksheet.get_all_values()) > 1:  # If there are rows after header
                worksheet.delete_rows(2, len(worksheet.get_all_values()))
            
            # Convert data to 2D array for batch update
            values = []
            for row_data in rows:
                # Prepare the row with proper formatting
                row = []
                for i, value in enumerate(row_data):
                    if value is None:
                        row.append('')
                    elif i == 0:  # Column A - force text format
                        # For column A, always treat as text and preserve exact format
                        row.append(str(value))
                    else:
                        # For other columns, keep original type
                        row.append(value)
                values.append(row)
            
            # Write all data at once with RAW input option to prevent any interpretation
            if values:
                # First, write the data with RAW format to prevent any interpretation
                worksheet.append_rows(values, value_input_option='RAW')
                
                # Then update column A with text format to ensure it stays as-is
                col_a_values = [[str(row[0])] for row in values]  # Get column A values as strings
                worksheet.update(f'A2:A{len(values)+1}', col_a_values, value_input_option='USER_ENTERED')
                
                # Set the format for column A to text
                worksheet.format('A2:A', {
                    'numberFormat': {
                        'type': 'TEXT'
                    },
                    'horizontalAlignment': 'CENTER'
                })
            
            # Apply number formats
            # Column A: Text format
            worksheet.format('A2:A', {
                'numberFormat': {
                    'type': 'TEXT'
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Column B: Whole number
            worksheet.format('B2:B', {
                'numberFormat': {
                    'type': 'NUMBER',
                    'pattern': '0'
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Column C: Number with 2 decimals
            worksheet.format('C2:C', {
                'numberFormat': {
                    'type': 'NUMBER',
                    'pattern': '0.00'
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Columns D, E: Text format
            worksheet.format('D2:E', {
                'numberFormat': {
                    'type': 'TEXT'
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Column F: Number with 2 decimals
            worksheet.format('F2:F', {
                'numberFormat': {
                    'type': 'NUMBER',
                    'pattern': '0.00'
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Column G: Text format (client)
            worksheet.format('G2:G', {
                'horizontalAlignment': 'CENTER'
            })
            
            # Apply font styles to columns
            # Column A: סיכום - bold #7f007f
            worksheet.format(f'A2:A{len(rows)+1}', {
                'textFormat': {
                    'bold': True,
                    'foregroundColor': {'red': 0.5, 'green': 0.0, 'blue': 0.5}  # #7f007f
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Column B: הנחה % - not bold, black
            worksheet.format(f'B2:B{len(rows)+1}', {
                'textFormat': {
                    'bold': False,
                    'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}  # Black
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Column C: תמחור שעה - not bold, black
            worksheet.format(f'C2:C{len(rows)+1}', {
                'textFormat': {
                    'bold': False,
                    'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}  # Black
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Column D: מדריך - not bold #007f00
            worksheet.format(f'D2:D{len(rows)+1}', {
                'textFormat': {
                    'bold': False,
                    'foregroundColor': {'red': 0.0, 'green': 0.5, 'blue': 0.0}  # #007f00
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Column E: לפי מדריך - not bold #007f00
            worksheet.format(f'E2:E{len(rows)+1}', {
                'textFormat': {
                    'bold': False,
                    'foregroundColor': {'red': 0.0, 'green': 0.5, 'blue': 0.0}  # #007f00
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Column F: סהכ שעות - bold #7f007f
            worksheet.format(f'F2:F{len(rows)+1}', {
                'textFormat': {
                    'bold': True,
                    'foregroundColor': {'red': 0.5, 'green': 0.0, 'blue': 0.5}  # #7f007f
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Column G: לקוח - bold #7f007f
            worksheet.format(f'G2:G{len(rows)+1}', {
                'textFormat': {
                    'bold': True,
                    'foregroundColor': {'red': 0.5, 'green': 0.0, 'blue': 0.5}  # #7f007f
                },
                'horizontalAlignment': 'CENTER'
            })
            
            # Format all headers to be bold and blue with light gray background
            header_range = f'A1:{chr(64 + len(headers))}1'  # A1:G1 for 7 columns
            worksheet.format(header_range, {
                'textFormat': {
                    'bold': True,
                    'foregroundColor': {'red': 0.0, 'green': 0.0, 'blue': 1.0}  # Blue color
                },
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},  # #e5e5e5 equivalent
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE'
            })
            
            # Format all data cells to have white background
            if len(rows) > 0:
                data_range = f'A2:{chr(64 + len(headers))}{len(rows) + 1}'
                worksheet.format(data_range, {
                    'backgroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}  # White background
                })
        
        return jsonify({
            'success': True,
            'message': f'Data exported successfully to {worksheet_name}'
        })
        
    except Exception as e:
        print(f"Error exporting to Google Sheets: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to export data: {str(e)}'
        }), 500

@app.route('/api/get_rates_discounts', methods=['GET'])
def get_rates_discounts():
    """Fetch rates and discounts for a specific month and year."""
    try:
        month = int(request.args.get('month'))
        year = int(request.args.get('year'))
        
        # Get Hebrew month name
        hebrew_months = [
            'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
            'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'
        ]
        month_name = hebrew_months[month - 1]
        
        # Get Google Sheets client
        gc = get_gspread_client()
        spreadsheet_id = os.getenv('billing_SPREADSHEET_ID')
        
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet('תעריפים והנחות')
            records = worksheet.get_all_records()
            
            # Filter records for the requested month and year (compare numeric months)
            filtered_records = [
                {
                    'לקוח': record['לקוח'],
                    'חודש': record['חודש'],
                    'שנה': record['שנה'],
                    'סוג': record['סוג'],
                    'ערך': float(record['ערך']) if record['ערך'] else 0
                }
                for record in records
                if str(record.get('חודש', '')).strip() == str(month) 
                and str(record.get('שנה', '')).strip() == str(year)
            ]
            
            return jsonify({
                'success': True,
                'data': filtered_records
            })
            
        except gspread.exceptions.WorksheetNotFound:
            # If worksheet doesn't exist, return empty list
            return jsonify({
                'success': True,
                'data': []
            })
            
    except Exception as e:
        print(f"Error fetching rates and discounts: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'שגיאה בטעינת הנתונים: {str(e)}'
        }), 500

@app.route('/api/save_rate_discount', methods=['POST'])
def save_rate_discount():
    try:
        data = request.json
        client_name = data.get('client_name')
        change_type = data.get('change_type')  # 'תמחור שעה' or 'הנחה %'
        new_value = float(data.get('new_value', 0))
        month = int(data.get('month'))
        year = int(data.get('year'))
        
        if not client_name or not change_type:
            return jsonify({'success': False, 'error': 'חסרים פרטים נדרשים'}), 400
        
        # Get Hebrew month name
        hebrew_months = [
            'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
            'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'
        ]
        month_name = hebrew_months[month - 1]
        
        # Get Google Sheets client
        gc = get_gspread_client()
        spreadsheet_id = os.getenv('billing_SPREADSHEET_ID')
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        # Get or create the "תעריפים והנחות" worksheet
        try:
            worksheet = spreadsheet.worksheet('תעריפים והנחות')
        except gspread.exceptions.WorksheetNotFound:
            # Create the worksheet if it doesn't exist
            worksheet = spreadsheet.add_worksheet(title='תעריפים והנחות', rows=1000, cols=5)
            # Add headers
            headers = ['לקוח', 'חודש', 'שנה', 'סוג', 'ערך']
            worksheet.append_row(headers)
            
            # Format headers
            header_format = {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE'
            }
            worksheet.format('A1:E1', header_format)
        
        # Get all records
        records = worksheet.get_all_records()
        existing_row = None
        
        # Find if a matching record already exists
        for i, record in enumerate(records, start=2):  # Start from row 2 (1-based)
            try:
                if (record['לקוח'] == client_name and 
                    str(record['חודש']) == str(month) and 
                    str(record['שנה']) == str(year) and 
                    record['סוג'] == change_type):
                    
                    existing_row = i
                    break
            except Exception as e:
                print(f"Error checking row {i}: {str(e)}")
                continue
        
        # Determine the default value based on change_type
        default_value = 0.0  # Default for הנחה %
        if change_type == 'תמחור שעה':
            default_value = 350.0  # Default for תמחור שעה
        
        # If the new value is the same as default, we'll remove the row if it exists
        if abs(new_value - default_value) < 0.01:  # Using a small epsilon for float comparison
            if existing_row:
                # Delete the row
                worksheet.delete_rows(existing_row)
                return jsonify({
                    'success': True,
                    'message': f'{change_type} הוסר עבור {client_name} ({month_name} {year}) (הוחזר לערך ברירת מחדל)'
                })
            else:
                # No row to delete and no action needed as it's already default
                return jsonify({
                    'success': True,
                    'message': f'לא נדרש עדכון - {change_type} כבר בערך ברירת המחדל עבור {client_name} ({month_name} {year})'
                })
        
        # If we have a non-default value, update or insert the row
        if existing_row:
            # Update existing row
            worksheet.update_cell(existing_row, 5, new_value)  # Column 5 is 'ערך'
        else:
            # Insert new row
            worksheet.append_row([
                client_name,  # לקוח
                str(month),   # חודש (numeric)
                str(year),    # שנה
                change_type,  # סוג (תמחור שעה / הנחה %)
                new_value     # ערך
            ])
        
        return jsonify({
            'success': True,
            'message': f'{change_type} עודכן ל-{new_value} עבור {client_name} ({month_name} {year})'
        })
        
    except Exception as e:
        print(f"Error saving rate and discount: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'שגיאה בשמירת הנתונים: {str(e)}'
        }), 500

# Add instructor routes are implemented above

@app.route('/api/client_events')
def get_client_events():
    """API endpoint to get events for a specific client"""
    try:
        client_name = request.args.get('client_name')
        month = int(request.args.get('month', datetime.now().month))
        year = int(request.args.get('year', datetime.now().year))
        
        if not client_name:
            return jsonify({'status': 'error', 'message': 'Client name is required'}), 400
        
        # Calculate the date range for the selected month (in local timezone)
        local_tz = pytz.timezone('Asia/Jerusalem')
        start_date = local_tz.localize(datetime(year, month, 1))
        
        if month == 12:
            end_date = local_tz.localize(datetime(year + 1, 1, 1))
        else:
            end_date = local_tz.localize(datetime(year, month + 1, 1))
        
        # Fetch events from Google Calendar
        events = fetch_events_from_calendar(start_date, end_date)
        
        # Create instructor mapping
        instructors_map = create_instructors_map()
        
        # Filter and process events for this client
        client_events = []
        
        for event in events:
            event_summary = event.get('summary', '').strip()
            if client_name in event_summary:
                # Get organizer's email and map to instructor name
                organizer_email = event.get('organizer', {}).get('email', '')
                organizer_username = organizer_email.split('@')[0] if '@' in organizer_email else ''
                instructor_name = instructors_map.get(organizer_username, organizer_username)
                
                # Get event times
                start = parse_iso_datetime(event['start'].get('dateTime', event['start'].get('date')))
                end = parse_iso_datetime(event['end'].get('dateTime', event['end'].get('date')))
                
                if not start or not end:
                    continue
                
                # Convert to local timezone for consistent display
                if start.tzinfo is None:
                    start = local_tz.localize(start)
                if end.tzinfo is None:
                    end = local_tz.localize(end)
                
                duration_hours = (end - start).total_seconds() / 3600
                
                client_events.append({
                    'summary': event_summary,
                    'instructor': instructor_name,
                    'start': start.isoformat(),
                    'end': end.isoformat(),
                    'duration_hours': duration_hours
                })
        
        return jsonify({
            'status': 'success',
            'data': client_events
        })
        
    except Exception as e:
        print(f"ERROR in get_client_events: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/get_instructor_events', methods=['GET'])
def get_instructor_events():
    """Fetch events for a specific instructor and month."""
    try:
        instructor_name = request.args.get('instructor')
        month = int(request.args.get('month'))
        year = int(request.args.get('year'))
        
        if not instructor_name:
            return jsonify({'error': 'Instructor name is required'}), 400
        
        # Calculate date range for the month
        start_date = datetime(year, month, 1).isoformat() + 'Z'
        if month == 12:
            end_date = datetime(year + 1, 1, 1).isoformat() + 'Z'
        else:
            end_date = datetime(year, month + 1, 1).isoformat() + 'Z'
        
        # Fetch events from calendar
        service = get_calendar_service()
        if not service:
            return jsonify({'error': 'Failed to connect to Google Calendar'}), 500
            
        events_result = service.events().list(
            calendarId=os.getenv('CALENDAR_ID'),
            timeMin=start_date,
            timeMax=end_date,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Get valid client names from sheets
        valid_client_names = get_client_names_from_sheets()
        print(f"DEBUG: Found {len(valid_client_names)} valid client names")
        
        # Filter events for this instructor with valid client names
        instructor_events = []
        instructors_map = create_instructors_map()
        
        for event in events:
            # Skip events without an organizer
            if 'organizer' not in event or 'email' not in event['organizer']:
                continue
                
            # Get instructor name from email
            organizer_email = event['organizer']['email']
            username = organizer_email.split('@')[0]
            event_instructor = instructors_map.get(username, username)
            
            if event_instructor == instructor_name:
                event_title = event.get('summary', '').strip()
                
                # Check if event title contains any valid client name
                client_in_title = any(
                    client_name in event_title
                    for client_name in valid_client_names
                    if client_name  # Skip empty client names
                )
                
                if not client_in_title:
                    print(f"DEBUG: Skipping event - no valid client in title: {event_title}")
                    continue
                    
                # Format event data
                start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
                end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date'))
                
                try:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    duration_hours = (end_dt - start_dt).total_seconds() / 3600
                    
                    # Find the client name that matches the event title
                    client_name = next(
                        (name for name in valid_client_names if name in event_title),
                        event_title  # Fallback to event title if no exact match found
                    )
                    
                    instructor_events.append({
                        'title': event_title,
                        'date': start_dt.strftime('%d/%m/%Y'),
                        'time': f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}",
                        'duration': f"{duration_hours:.1f}",
                        'client': client_name
                    })
                except (ValueError, AttributeError) as e:
                    print(f"Error processing event time: {e}")
                    continue
        
        return jsonify({
            'success': True,
            'events': instructor_events
        })
        
    except Exception as e:
        print(f"Error fetching instructor events: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/export_payments', methods=['POST'])
def export_payments_to_sheets():
    try:
        data = request.json
        month = int(data.get('month'))
        year = int(data.get('year'))
        payment_data = data.get('data', [])
        
        if not payment_data:
            return jsonify({'success': False, 'error': 'No data to export'}), 400
        
        # Get Hebrew month name
        hebrew_months = [
            'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
            'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'
        ]
        worksheet_name = f"{hebrew_months[month-1]} {year}"
        
        # Get Google Sheets client
        gc = get_gspread_client()
        spreadsheet_id = os.getenv('payment_SPREADSHEET_ID')
        if not spreadsheet_id:
            return jsonify({'success': False, 'error': 'Payment spreadsheet ID not configured'}), 500
            
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        # Define headers in the specified RTL order
        headers = [
            'סיכום', 'שכר שעה', 'לקוח', 'לפי לקוח', 'סהכ שעות', 'מדריך'
        ]
        
        # Try to get the worksheet, create if it doesn't exist
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            # Clear existing content while preserving the worksheet
            if worksheet.row_count > 0:
                worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            # Create a new worksheet with exactly the number of rows needed
            num_rows = len(payment_data) + 1  # +1 for header row
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=num_rows,
                cols=6  # Exactly 6 columns as requested
            )
            
            # Set column widths (in pixels) for better readability
            column_widths = [
                {'startColumnIndex': 0, 'endColumnIndex': 1, 'pixelSize': 200},  # Column A: סיכום
                {'startColumnIndex': 1, 'endColumnIndex': 2, 'pixelSize': 100},  # Column B: שכר שעה
                {'startColumnIndex': 2, 'endColumnIndex': 3, 'pixelSize': 200},  # Column C: לקוח
                {'startColumnIndex': 3, 'endColumnIndex': 4, 'pixelSize': 100},  # Column D: לפי לקוח
                {'startColumnIndex': 4, 'endColumnIndex': 5, 'pixelSize': 100},  # Column E: סהכ שעות
                {'startColumnIndex': 5, 'endColumnIndex': 6, 'pixelSize': 200}   # Column F: מדריך
            ]
            
            # Apply column widths in a batch update
            body = {
                'requests': [{
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': worksheet.id,
                            'dimension': 'COLUMNS',
                            'startIndex': width['startColumnIndex'],
                            'endIndex': width['endColumnIndex']
                        },
                        'properties': {
                            'pixelSize': width['pixelSize']
                        },
                        'fields': 'pixelSize'
                    }
                } for width in column_widths]
            }
            
            try:
                spreadsheet.batch_update(body)
            except Exception as e:
                print(f"Warning: Could not set column widths: {e}")
        
        # Add headers to the worksheet
        worksheet.update('A1:F1', [headers])
        
        # Apply header formatting
        header_format = {
            'textFormat': {
                'bold': True,
                'foregroundColor': {'red': 0.0, 'green': 0.0, 'blue': 1.0}  # Blue color
            },
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},  # Light gray
            'horizontalAlignment': 'CENTER',
            'verticalAlignment': 'MIDDLE',
            'wrapStrategy': 'WRAP'  # Ensure text wraps in cells
        }
        worksheet.format('A1:F1', header_format)
        
        # Prepare data for export
        rows = []
        for item in payment_data:
            # Get values directly - they already have proper newline formatting from get_payment_data
            summary = str(item.get('summary', '')).strip()
            hourly_rate = str(item.get('hourly_rate', '')).strip()
            client = str(item.get('client', '')).strip()  # Already has newlines
            by_client = str(item.get('by_client', '')).strip()  # Already has newlines
            total_hours = str(item.get('total_hours', '')).strip()
            instructor = str(item.get('instructor', '')).strip()
            
            # Create the row with proper ordering
            row = [
                summary,         # סיכום
                hourly_rate,    # שכר שעה
                client,         # לקוח
                by_client,      # לפי לקוח
                total_hours,    # סהכ שעות
                instructor      # מדריך
            ]
            rows.append(row)
        
        # Update the worksheet with new data
        if rows:
            # We already cleared the worksheet, so we just need to append the data
            # Append rows with USER_ENTERED option to properly interpret newlines
            worksheet.append_rows(rows, value_input_option='USER_ENTERED')
        
        # Apply formatting to data rows
        if rows:
            # Define the data range (A2 to F{last_row})
            data_range = f'A2:F{len(rows) + 1}'
            
            # Common cell format
            cell_format = {
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE',
                'wrapStrategy': 'WRAP',  # Ensure text wraps in cells
                'borders': {
                    'top': {'style': 'SOLID'},
                    'bottom': {'style': 'SOLID'},
                    'left': {'style': 'SOLID'},
                    'right': {'style': 'SOLID'}
                }
            }
            
            # Apply common format to all cells
            worksheet.format(data_range, cell_format)
            
            # Apply specific formatting to columns
            # סיכום (A) - Bold green
            worksheet.format(f'A2:A{len(rows) + 1}', {
                'textFormat': {'bold': True, 'foregroundColor': {'red': 0, 'green': 0.4, 'blue': 0}}
            })
            
            # שכר שעה (B) - Regular black
            worksheet.format(f'B2:B{len(rows) + 1}', {
                'textFormat': {'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}}
            })
            
            # לקוח (C) and לפי לקוח (D) - Purple
            worksheet.format(f'C2:D{len(rows) + 1}', {
                'textFormat': {'foregroundColor': {'red': 1, 'green': 0, 'blue': 1}},
                'horizontalAlignment': 'CENTER',  # Center align text
                'wrapStrategy': 'WRAP',  # Ensure text wrapping
                'verticalAlignment': 'MIDDLE'  # Center vertically
            })
            
            # סהכ שעות (E) and מדריך (F) - Bold green
            worksheet.format(f'E2:F{len(rows) + 1}', {
                'textFormat': {'bold': True, 'foregroundColor': {'red': 0, 'green': 0.4, 'blue': 0}}
            })
        
        # Set column widths (in pixels)
        column_widths = [
            {'startColumn': 1, 'endColumn': 2, 'width': 100},  # סיכום
            {'startColumn': 2, 'endColumn': 3, 'width': 80},   # שכר שעה
            {'startColumn': 3, 'endColumn': 4, 'width': 150},  # לקוח
            {'startColumn': 4, 'endColumn': 5, 'width': 150},  # לפי לקוח
            {'startColumn': 5, 'endColumn': 6, 'width': 80},   # סהכ שעות
            {'startColumn': 6, 'endColumn': 7, 'width': 150}   # מדריך
        ]
        
        # Apply column widths
        for width_setting in column_widths:
            worksheet.set_column(
                width_setting['startColumn'] - 1,  # Convert to 0-based index
                width_setting['endColumn'] - 1,
                width_setting['width'] / 7  # Convert pixels to character width (approximate)
            )
        
        # Set row heights to auto (adjusts to content)
        worksheet.freeze(1, 0)  # Freeze header row
        worksheet.set_basic_filter()  # Add filter to header row
        
        return jsonify({
            'success': True,
            'message': f'Data exported successfully to {worksheet_name}'
        })
        
    except Exception as e:
        print(f"Error exporting payments to Google Sheets: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to export data: {str(e)}'
        }), 500

def save_hourly_wage(instructor_name, month, year, hourly_wage):
    """Save the hourly wage to Google Sheets."""
    try:
        # Get Google Sheets client
        gc = get_gspread_client()
        spreadsheet_id = os.getenv('payment_SPREADSHEET_ID')
        
        if not spreadsheet_id:
            raise Exception('payment_SPREADSHEET_ID not found in environment variables')
        
        # Open the spreadsheet
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        # Try to open the 'שכר שעה' worksheet, create if it doesn't exist
        try:
            worksheet = spreadsheet.worksheet('שכר שעה')
        except gspread.WorksheetNotFound:
            # Create the worksheet with headers if it doesn't exist
            worksheet = spreadsheet.add_worksheet(title='שכר שעה', rows=1000, cols=5)
            # Add headers
            worksheet.append_row(['מדריך', 'חודש', 'שנה', 'שכר שעה', 'תאריך עדכון'])
            return True  # No need to do anything else if the worksheet was just created
        
        # Get all records
        records = worksheet.get_all_records()
        
        # Check if there's an existing record for this instructor, month, and year
        row_num = None
        for i, record in enumerate(records, start=2):  # Start from row 2 (1-based)
            if (str(record.get('מדריך', '')).strip() == instructor_name and 
                int(record.get('חודש', 0)) == month and 
                int(record.get('שנה', 0)) == year):
                row_num = i
                break
        
        DEFAULT_HOURLY_WAGE = 200  # Default hourly wage
        
        # If the wage is the default value, remove the record if it exists
        if abs(float(hourly_wage) - DEFAULT_HOURLY_WAGE) < 0.01:  # Using a small epsilon for float comparison
            if row_num:
                worksheet.delete_rows(row_num)
                return True
            return True  # No action needed if it doesn't exist and we're setting to default
        
        # Prepare the row data
        row_data = [instructor_name, month, year, hourly_wage, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        
        if row_num:
            # Update existing record
            for i, value in enumerate(row_data, start=1):
                worksheet.update_cell(row_num, i, value)
        else:
            # Add new record
            worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        print(f"Error saving hourly wage: {e}")
        return False

def get_hourly_wage(instructor_name, month, year):
    """Get the hourly wage for an instructor for a specific month and year.
    
    Returns:
        float: The hourly wage, or 200 (default) if no specific wage is set
    """
    try:
        DEFAULT_HOURLY_WAGE = 200  # Default hourly wage
        
        # Get Google Sheets client
        gc = get_gspread_client()
        spreadsheet_id = os.getenv('payment_SPREADSHEET_ID')
        
        if not spreadsheet_id:
            return DEFAULT_HOURLY_WAGE
            
        # Open the spreadsheet and worksheet
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        try:
            worksheet = spreadsheet.worksheet('שכר שעה')
            records = worksheet.get_all_records()
            
            # Find the most recent record for this instructor, month, and year
            for record in reversed(records):
                if (str(record.get('מדריך', '')).strip() == instructor_name and 
                    int(record.get('חודש', 0)) == month and 
                    int(record.get('שנה', 0)) == year):
                    return float(record.get('שכר שעה', DEFAULT_HOURLY_WAGE))
            
            return DEFAULT_HOURLY_WAGE  # Return default if no record found
            
        except gspread.WorksheetNotFound:
            return DEFAULT_HOURLY_WAGE  # Return default if worksheet doesn't exist
            
    except Exception as e:
        print(f"Error getting hourly wage: {e}")
        return None

@app.route('/api/update_hourly_rate', methods=['POST'])
def update_hourly_rate():
    """Update the hourly rate for an instructor."""
    try:
        data = request.get_json()
        instructor_name = data.get('instructor')
        month = int(data.get('month'))
        year = int(data.get('year'))
        hourly_rate = int(round(float(data.get('hourly_rate', 0))))  # Round to nearest integer
        
        if not instructor_name:
            return jsonify({'success': False, 'error': 'Instructor name is required'}), 400
        
        # Save the hourly wage to Google Sheets
        if not save_hourly_wage(instructor_name, month, year, hourly_rate):
            return jsonify({'success': False, 'error': 'Failed to save hourly wage'}), 500
        
        # Get the billing data
        billing_data = get_payment_data(month, year)
        
        # Find the instructor in the records and update their hourly rate
        for record in billing_data.get('records', []):
            if record['instructor'] == instructor_name:
                # Store as integer value without decimals
                record['hourly_rate'] = f"{hourly_rate:,.0f}"
                # Recalculate total payment
                total_hours = float(record['total_hours'].replace(',', ''))
                total_payment = total_hours * hourly_rate
                # Format total payment with 2 decimal places for consistency
                record['total_payment'] = f"{total_payment:,.2f}"
                break
        
        return jsonify({
            'success': True,
            'message': 'Hourly rate updated successfully',
            'total_payment': record.get('total_payment', '0.00'),  # Return updated total payment
            'hourly_rate': f"{hourly_rate:,.0f}"  # Return the rounded hourly rate
        })
        
    except Exception as e:
        print(f"Error updating hourly rate: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
