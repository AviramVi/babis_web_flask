from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from dotenv import load_dotenv
from utils.google_sheets import (
    fetch_instructors,
    fetch_clients,
    update_instructor,
    add_instructor,
    get_sheet_data,
    fetch_billing_data,  # Add this line
    get_billing_worksheets,  # Add this line
    get_payment_worksheets,
    fetch_payment_data,
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
    return render_template('instructors.html', headers=headers, instructors=instructors)

@app.route('/update_instructor', methods=['POST'])
def update_instructor_route():
    data = request.json
    row_index = data.get('index')  # This is the row index in the Google Sheet
    instructor_data = data.get('data')  # This is the updated instructor data
    
    sheet_name = os.getenv("INSTRUCTORS_SHEET_NAME")
    
    try:
        # Get headers once
        headers, _ = get_sheet_data(sheet_name)
        
        # Prepare a single batch update with all fields
        updates = {}
        
        # Process all regular fields
        for col_name, value in instructor_data.items():
            if col_name in headers:
                col_index = headers.index(col_name) + 1  # +1 for 1-indexing in Google Sheets
                updates[col_index] = value
            elif col_name == 'סטטוס':
                # Handle the active status field (column F, which is index 6)
                updates[6] = value
        
        # Send a single batch update to the sheet
        if updates:
            update_instructor(sheet_name, row_index, updates)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating instructor: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clients/private')
def clients_private():
    sheet_name = os.getenv("clients_private_SHEET_NAME")
    headers, clients = get_sheet_data(sheet_name)
    return render_template('clients_private.html', headers=headers, clients=clients)

@app.route('/clients/institutional')
def clients_institutional():
    sheet_name = os.getenv("clients_institutional_SHEET_NAME")
    headers, clients = get_sheet_data(sheet_name)
    # Arrange headers in the desired order
    desired_headers = ['גוף', 'איש קשר', 'טלפון', 'מייל', 'הערות']
    # Filter only headers that exist in the worksheet
    headers = [h for h in desired_headers if h in headers]
    return render_template('clients_institutional.html', headers=headers, clients=clients)

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
        start = event['start'].get('dateTime', event['start'].get('date'))
        try:
            dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        except Exception:
            dt = datetime.strptime(start, "%Y-%m-%d")
        day = dt.day
        time_str = dt.strftime('%H:%M') if 'T' in start else ''
        title = event.get('summary', '')
        if day not in events_by_day:
            events_by_day[day] = []
        events_by_day[day].append({'time': time_str, 'title': title})

    # Hebrew day names (RTL order)
    hebrew_days = ["שבת", "שישי", "חמישי", "רביעי", "שלישי", "שני", "ראשון"]
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

# Add instructor routes are implemented above

if __name__ == '__main__':
    app.run(debug=True)