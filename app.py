from flask import Flask, render_template, request, redirect, url_for, jsonify, session
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

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session
load_dotenv()

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
    data = request.json
    sheet_row = data.get('sheet_row')
    client_data = data.get('data')
    sheet_name = os.getenv("clients_private_SHEET_NAME")
    
    try:
        # Get headers from first row
        headers = ['שם', 'טלפון', 'מייל', 'צורך מיוחד', 'הערות', 'פעיל']
        
        # Create ordered list of values based on header order
        values = [
            client_data.get('שם', ''),
            client_data.get('טלפון', ''),
            client_data.get('מייל', ''),
            client_data.get('צורך מיוחד', ''),
            client_data.get('הערות', ''),
            client_data.get('פעיל', '')
        ]

        # Create cell updates
        updates = {}
        for idx, value in enumerate(values, start=1):
            updates[idx] = value
        
        # Send a single batch update to the sheet
        if updates:
            update_instructor(sheet_name, sheet_row, updates)  # Reusing the same function as it has the same logic
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating private client: {e}")
        return jsonify({'success': False, 'error': str(e)})

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
    worksheet_names = get_payment_worksheets()
    selected_worksheet = request.args.get('worksheet', worksheet_names[0] if worksheet_names else None)
    headers, payment_records = fetch_payment_data(selected_worksheet)
    # Use the requested headers and order
    desired_headers = ['מדריך', 'סהכ שעות', 'לפי לקוח', 'לקוח', 'שכר שעה', 'סיכום']
    headers = desired_headers
    return render_template(
        'payments.html',
        headers=headers,
        records=payment_records,
        worksheet_names=worksheet_names,
        selected_worksheet=selected_worksheet
    )

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
    try:
        # Get month and year from query parameters
        month = int(request.args.get('month', datetime.now().month))
        year = int(request.args.get('year', datetime.now().year))
        include_rates = request.args.get('include_rates', 'false').lower() == 'true'
        
        # Get all valid client names from Google Sheets (with caching)
        valid_client_names = get_client_names_from_sheets()
        
        # Create instructor mapping (with caching)
        instructors_map = create_instructors_map()
        
        # Calculate the date range for the selected month
        local_tz = pytz.timezone('Asia/Jerusalem')
        start_date = local_tz.localize(datetime(year, month, 1))
        end_date = local_tz.localize(datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1))
        
        # Cache key for calendar events
        cache_key = f'calendar_events_{year}_{month}'
        events = None
        
        # Try to get events from cache first
        if cache_key in session:
            events = session[cache_key]
        else:
            # Fetch events from Google Calendar if not in cache
            events = fetch_events_from_calendar(start_date, end_date)
            # Store in session cache for 1 hour
            session[cache_key] = events
        
        # Process events to group by client and calculate hours
        client_data = {}
        
        for event in events:
            try:
                # Get the event summary/title
                event_summary = event.get('summary', '').strip()
                if not event_summary:
                    continue
                
                # Find if any client name is present in the event title
                client_name = None
                for name in valid_client_names:
                    if name and name in event_summary:
                        client_name = name
                        break
                
                # Skip events that don't contain any valid client name
                if not client_name:
                    continue
                
                # Get organizer's email and map to instructor name
                organizer_email = event.get('organizer', {}).get('email', '')
                organizer_username = organizer_email.split('@')[0] if '@' in organizer_email else ''
                instructor_name = instructors_map.get(organizer_username, organizer_username)
                
                # Calculate event duration in hours
                start = parse_iso_datetime(event['start'].get('dateTime', event['start'].get('date')))
                end = parse_iso_datetime(event['end'].get('dateTime', event['end'].get('date')))
                
                if not start or not end:
                    continue
                
                # Convert to local timezone for consistent calculation
                if start.tzinfo is None:
                    start = local_tz.localize(start)
                if end.tzinfo is None:
                    end = local_tz.localize(end)
                
                duration_hours = (end - start).total_seconds() / 3600
                
                # Initialize client data if not exists
                if client_name not in client_data:
                    client_data[client_name] = {
                        'total_hours': 0,
                        'instructors': {}
                    }
                
                # Update client's total hours
                client_data[client_name]['total_hours'] += duration_hours
                
                # Update instructor hours
                if instructor_name not in client_data[client_name]['instructors']:
                    client_data[client_name]['instructors'][instructor_name] = 0
                client_data[client_name]['instructors'][instructor_name] += duration_hours
                
            except Exception as e:
                # Silently skip problematic events
                continue
        
        # Format the data for the frontend
        billing_data = []
        
        # Add rates and discounts if they exist
        # Set default rate to 350 if not specified
        default_rate = 350
        
        # Get rates and discounts if requested
        rates_and_discounts = {}
        if include_rates:
            try:
                # Get rates and discounts for the month/year
                month_str = str(month)
                year_str = str(year)
                rates_response = get_rates_discounts_internal(month_str, year_str)
                if rates_response and isinstance(rates_response, list):
                    for item in rates_response:
                        client_name = item.get('לקוח')
                        if client_name:
                            if client_name not in rates_and_discounts:
                                rates_and_discounts[client_name] = {}
                            if 'תמחור שעה' in item:
                                rates_and_discounts[client_name]['תמחור שעה'] = item['תמחור שעה']
                            if 'הנחה %' in item:
                                rates_and_discounts[client_name]['הנחה %'] = item['הנחה %']
            except Exception as e:
                # If rates/discounts fail, continue without them
                print(f"Error getting rates and discounts: {e}")
        
        for client_name, data in client_data.items():
            # Format instructor hours for display
            instructor_hours = []
            instructor_names = []
            
            for name, hours in data['instructors'].items():
                instructor_hours.append(f"{name}: {hours:.2f}")
                instructor_names.append(name)
            
            # Get client-specific rate and discount if available
            client_rate = default_rate
            client_discount = 0
            
            if client_name in rates_and_discounts:
                client_data_rates = rates_and_discounts[client_name]
                if 'תמחור שעה' in client_data_rates:
                    client_rate = float(client_data_rates['תמחור שעה'])
                if 'הנחה %' in client_data_rates:
                    client_discount = float(client_data_rates['הנחה %'])
            
            # Calculate total with applied discount
            total = data['total_hours'] * client_rate * (1 - client_discount/100)
            
            # Create the record
            record = {
                'לקוח': client_name,
                'סהכ שעות': round(data['total_hours'], 2),
                'לפי מדריך': '\n'.join(instructor_hours),
                'מדריך': '\n'.join(instructor_names),
                'תמחור שעה': client_rate,
                'הנחה %': client_discount,
                'סיכום': round(total, 2)
            }
            
            billing_data.append(record)
        
        response_data = {
            'status': 'success',
            'data': billing_data
        }
        
        # Include rates and discounts in the response if requested
        if include_rates:
            response_data['rates'] = rates_and_discounts
            
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

    # Days in month
    days_in_month = pycalendar.monthrange(year, month)[1]

    return render_template(
        'calendar.html',
        year=year,
        month=month,
        month_name=hebrew_months[month],
        hebrew_days=hebrew_days,
        days_in_month=days_in_month,
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
            # Create a new worksheet with headers and formatting
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
            worksheet.append_row(headers)
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
            row = [
                get_value('סיכום'),
                get_value('הנחה %', is_percent=True),
                get_value('תמחור שעה'),
                get_value('מדריך', keep_newlines=True),  # Keep newlines for these columns
                get_value('לפי מדריך', keep_newlines=True),  # Keep newlines for these columns
                get_value('סהכ שעות'),
                get_value('לקוח')
            ]
            rows.append(row)
        
        # Add data to worksheet
        if rows:
            worksheet.append_rows(rows)
            
            # Format number columns with new positions (adjusted for removed column)
            # A: סיכום, B: הנחה %, C: תמחור שעה, F: סהכ שעות
            number_columns = {
                'A': '0.00',   # סיכום
                'B': '0',      # הנחה %
                'C': '0.00',   # תמחור שעה
                'F': '0.00'    # סהכ שעות
            }
            
            # Apply number formatting
            for col, format_str in number_columns.items():
                range_str = f"{col}2:{col}{len(rows)+1}"
                worksheet.format(range_str, {
                    'numberFormat': {
                        'type': 'NUMBER',
                        'pattern': format_str
                    },
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

# Helper function to get rates and discounts without going through API
def get_rates_discounts_internal(month, year):
    """Get rates and discounts for specific month/year without creating a new HTTP request"""
    try:
        # Cache key for rates and discounts
        cache_key = f'rates_discounts_{year}_{month}'
        
        # Check if we have cached data
        if cache_key in session:
            return session[cache_key]
        
        # Get rates/discounts from the database
        gc = get_gspread_client()
        
        # Get the spreadsheet ID from environment variables
        spreadsheet_id = os.getenv('billing_SPREADSHEET_ID')
        if not spreadsheet_id:
            return []
        
        # Open the spreadsheet
        spreadsheet = gc.open_by_key(spreadsheet_id)
        
        try:
            worksheet = spreadsheet.worksheet('תעריפים והנחות')
            records = worksheet.get_all_records()
            
            # Filter records for the requested month and year
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
            
            # Process records to create a client-based lookup
            client_rates = {}
            
            for record in filtered_records:
                client_name = record['לקוח']
                rate_type = record['סוג']  # 'תמחור שעה' or 'הנחה %'
                value = record['ערך']
                
                if client_name not in client_rates:
                    client_rates[client_name] = {}
                    
                client_rates[client_name][rate_type] = value
            
            # Cache the results
            session[cache_key] = client_rates
            
            return client_rates
            
        except gspread.exceptions.WorksheetNotFound:
            # If worksheet doesn't exist, return empty dict
            return {}
    except Exception as e:
        print(f"Error in get_rates_discounts_internal: {e}")
        return {}

@app.route('/api/get_rates_discounts', methods=['GET'])
def get_rates_discounts():
    try:
        month = request.args.get('month')
        year = request.args.get('year')
        
        if not month or not year:
            return jsonify({
                'success': False,
                'error': 'חסרים פרטי חודש/שנה'  # Missing month/year details
            }), 400
        
        # Use the internal helper function to get rates and discounts
        client_rates = get_rates_discounts_internal(month, year)
        
        # Convert the client_rates dictionary to a list format for the API response
        result_records = []
        
        for client_name, rates in client_rates.items():
            for rate_type, value in rates.items():
                result_records.append({
                    'לקוח': client_name,  # Client name
                    'חודש': month,      # Month
                    'שנה': year,        # Year
                    'סוג': rate_type,   # Type (rate or discount)
                    'ערך': value        # Value
                })
        
        return jsonify({
            'success': True,
            'data': result_records
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
        
        # Check if a row with the same client, month, year, and change type already exists
        records = worksheet.get_all_records()
        row_updated = False
        
        # Start from row 2 (1-based) since row 1 is headers
        for i in range(2, len(records) + 2):
            try:
                client = worksheet.cell(i, 1).value
                record_month = worksheet.cell(i, 2).value
                record_year = worksheet.cell(i, 3).value
                record_type = worksheet.cell(i, 4).value
                
                if (client == client_name and 
                    str(record_month) == str(month) and 
                    str(record_year) == str(year) and 
                    record_type == change_type):
                    
                    # Update the existing row's value
                    worksheet.update_cell(i, 5, new_value)
                    row_updated = True
                    break
                    
            except Exception as e:
                print(f"Error checking row {i}: {str(e)}")
                continue
        
        # If no existing row was found, append a new one
        if not row_updated:
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

if __name__ == '__main__':
    app.run(debug=True)