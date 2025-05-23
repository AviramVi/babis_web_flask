from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
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
    update_row
)
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import calendar as pycalendar
import pytz
from datetime import datetime, timedelta, date

app = Flask(__name__)
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

@app.route('/billing')
def billing():
    worksheet_names = get_billing_worksheets()
    selected_worksheet = request.args.get('worksheet', worksheet_names[0] if worksheet_names else None)

    headers, billing_records = fetch_billing_data(selected_worksheet)
    desired_headers = ['לקוח', 'סהכ שעות', 'לפי מדריך', 'מדריך', 'תמחור שעה', 'הנחה %', 'סיכום']

    return render_template('billing.html',
                         headers=desired_headers,
                         records=billing_records,
                         worksheet_names=worksheet_names,
                         selected_worksheet=selected_worksheet)

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

# Add instructor routes are implemented above

if __name__ == '__main__':
    app.run(debug=True)