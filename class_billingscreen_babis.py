from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
                            QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox,
                            QPushButton, QInputDialog, QMessageBox, QLineEdit, QAbstractItemDelegate)
from PyQt6.QtCore import Qt, QDate, QTimer, QEvent, QObject
from PyQt6.QtGui import QFont, QColor, QKeyEvent, QDoubleValidator, QIntValidator


class RateItemDelegate(QItemDelegate):
    """Custom delegate for rate and discount columns"""
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            # Set up validator for numeric input
            validator = QDoubleValidator()
            validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            validator.setDecimals(2)
            
            # Set range based on column (rate or discount)
            if index.column() == 4:  # Rate column
                validator.setBottom(0)
            else:  # Discount column
                validator.setBottom(0)
                validator.setTop(100)
                
            editor.setValidator(validator)
            editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return editor


class BillingScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #d3d3d3;")
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Header layout - RTL adjusted
        header_layout = QHBoxLayout()
        
        # Month/Year dropdown (right side)
        self.month_year_combo = QComboBox()
        self.month_year_combo.setFont(QFont("Arial", 16))
        self.month_year_combo.setStyleSheet("""
            QComboBox {
                min-width: 150px;
                color: black;
                background-color: white;
                text-align: center;
                padding: 2px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QComboBox:hover {
                background-color: #ADD8E6;
            }
            QComboBox QAbstractItemView {
                text-align: center;
                color: black;
                background-color: white;
                border: 1px solid #ccc;
                selection-background-color: #ADD8E6;
                padding: 4px;
            }
        """)
        
        # Force center alignment
        self.month_year_combo.setEditable(True)
        line_edit = self.month_year_combo.lineEdit()
        line_edit.setReadOnly(True)
        line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title (left side)
        header = QLabel("חיובים", self)
        header.setFont(QFont("Arial", int(40 * 1.3), QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: blue; background: transparent;")

        # Populate with guaranteed current month
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        hebrew_months = [
            "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
            "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
        ]
        
        # Add current month first
        current_text = f"{hebrew_months[current_month-1]} {current_year}"
        self.month_year_combo.addItem(current_text, (current_month, current_year))
        
        # Add surrounding years
        for year in [current_year-1, current_year, current_year+1]:
            for month_idx, month in enumerate(hebrew_months, 1):
                if not (month_idx == current_month and year == current_year):
                    self.month_year_combo.addItem(f"{month} {year}", (month_idx, year))

        # Set current index
        current_index = max(0, self.month_year_combo.findData((current_month, current_year)))
        self.month_year_combo.setCurrentIndex(current_index)
        # Connect combo changes to data refresh
        self.month_year_combo.currentIndexChanged.connect(self.populate_billing_data)
        # Add to layout (RTL: combo first -> right side)
        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(self.month_year_combo)
        main_layout.addLayout(header_layout)

        # Table
        self.table = ResizableTable(self)
        header_font_size = int(17 * 1.3)
        header_style = f"QHeaderView::section {{ color: blue; font-weight: bold; font-family: Arial; font-size: {header_font_size}px; }}"
        self.table.horizontalHeader().setStyleSheet(header_style)
        self.table.verticalHeader().setStyleSheet(header_style)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Enable editing on double-click, F2, or single click
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.EditKeyPressed |
            QAbstractItemView.EditTrigger.SelectedClicked
        )
        
        self.table.setSortingEnabled(True)
        self.table.cellClicked.connect(self.handle_cell_click)
        self.table.setColumnCount(7)  # Changed from 6 to 7
        self.table.setHorizontalHeaderLabels(["לקוח", "סהכ שעות", "לפי מדריך", "מדריך", "תמחור שעה", "הנחה %", "סיכום"])
        
        # Set selection behavior and style
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setStyleSheet("""
            QTableView {
                selection-background-color: #ADD8E6;
                selection-color: black;
            }
            QTableView::item:selected {
                background-color: #ADD8E6;
                color: black;
            }
            QTableView::item:hover {
                background-color: #ADD8E6;
            }
        """)
        
        # Set row height
        default_height = self.table.verticalHeader().defaultSectionSize()
        self.table.verticalHeader().setDefaultSectionSize(int(default_height * 1.3 * 1.3))
        
        # Set up custom delegates for rate and discount columns
        rate_delegate = RateItemDelegate(self.table)
        self.table.setItemDelegateForColumn(4, rate_delegate)  # תמחור שעה
        self.table.setItemDelegateForColumn(5, rate_delegate)  # הנחה %
        
        # Add to layout
        main_layout.addWidget(self.table)

        # Bottom buttons container
        bottom_buttons = QHBoxLayout()
        
        # Back Button (left side)
        self.back_btn = QPushButton("חזרה", self)
        self.back_btn.setFixedWidth(120)
        self.back_btn.setFont(QFont("Arial", int(14 * 1.3)))
        self.back_btn.setStyleSheet("color: black;")
        self.back_btn.clicked.connect(self.go_back)
        bottom_buttons.addWidget(self.back_btn)

        bottom_buttons.addStretch()  # This pushes the buttons to opposite sides

        # Export Button (right side)
        self.export_btn = QPushButton("העברה לאקסל", self)
        self.export_btn.setFixedWidth(120)
        self.export_btn.setFont(QFont("Arial", int(14 * 1.3)))
        self.export_btn.setStyleSheet("color: black;")
        bottom_buttons.addWidget(self.export_btn)

        main_layout.addLayout(bottom_buttons)

        self.setLayout(main_layout)
        
        # Initialize cell values dictionary to store rates per client per month
        self.cell_values = {}
        
        # Load saved cell values
        self.load_cell_values()
        
        self.instructors_map = self._create_instructors_map()
        self.populate_billing_data()

        # Connect signals
        self.export_btn.clicked.connect(self.export_to_sheets)
        self.table.itemChanged.connect(self.save_edited_cell)

    def get_current_month_year_key(self):
        """Get a string key for the current month and year"""
        month, year = self.month_year_combo.currentData()
        return f"{month}-{year}"
    
    def load_cell_values(self):
        """Load values for תמחור שעה and הנחה % columns from Google Sheets"""
        try:
            gc = get_gspread_client()
            spreadsheet_id = os.getenv("billing_SPREADSHEET_ID")
            if not spreadsheet_id:
                return
                
            sh = gc.open_by_key(spreadsheet_id)
            
            # Try to get the values worksheet
            try:
                worksheet = sh.worksheet("תעריפים והנחות")
                values_data = worksheet.get_all_records()
                
                # Convert to dictionary format
                for record in values_data:
                    if 'לקוח' in record and 'חודש' in record and 'שנה' in record and 'סוג' in record and 'ערך' in record:
                        client_name = record['לקוח']
                        month = record['חודש']
                        year = record['שנה']
                        column_type = record['סוג']  # "תמחור שעה" or "הנחה %"
                        value = record['ערך']
                        
                        # Create a unique key for this cell: client-month-year-column_type
                        cell_key = f"{client_name}-{month}-{year}-{column_type}"
                        self.cell_values[cell_key] = value
            except:
                # Create worksheet if it doesn't exist
                worksheet = sh.add_worksheet("תעריפים והנחות", rows=100, cols=5)
                worksheet.update('A1:E1', [['לקוח', 'חודש', 'שנה', 'סוג', 'ערך']])
        except Exception as e:
            print(f"Error loading cell values: {e}")
    
    def save_cell_value(self, client_name, column_type, value):
        """Save or update an individual cell's value in Google Sheets
        
        Args:
            client_name: The name of the client
            column_type: Either "תמחור שעה" or "הנחה %"
            value: The numeric value to save
        """
        try:
            gc = get_gspread_client()
            spreadsheet_id = os.getenv("billing_SPREADSHEET_ID")
            if not spreadsheet_id:
                return
                
            sh = gc.open_by_key(spreadsheet_id)
            
            # Get current month and year
            month, year = self.month_year_combo.currentData()
            
            try:
                worksheet = sh.worksheet("תעריפים והנחות")
            except:
                # Create worksheet if it doesn't exist
                worksheet = sh.add_worksheet("תעריפים והנחות", rows=100, cols=5)
                worksheet.update('A1:E1', [['לקוח', 'חודש', 'שנה', 'סוג', 'ערך']])
            
            # Create a unique key for this cell
            cell_key = f"{client_name}-{month}-{year}-{column_type}"
            
            # Store in memory
            self.cell_values[cell_key] = value
            
            # Check if this cell already exists in the worksheet
            found = False
            all_data = worksheet.get_all_records()
            for idx, record in enumerate(all_data):
                if (record.get('לקוח') == client_name and 
                    record.get('חודש') == month and 
                    record.get('שנה') == year and
                    record.get('סוג') == column_type):
                    # Update existing record
                    row = idx + 2  # +2 for header and 1-based indexing
                    worksheet.update_cell(row, 5, value)
                    found = True
                    break
            
            if not found:
                # Add new record
                next_row = len(all_data) + 2  # +2 for header row and 1-based indexing
                worksheet.update(f'A{next_row}:E{next_row}', 
                                [[client_name, month, year, column_type, value]])
        except Exception as e:
            print(f"Error saving cell value: {e}")

    def get_current_month_events(self, full_events=False):
        """Fetch events for current month and return customer names with hours and organizers.
        If full_events=True, return the raw event list with matched_client field.
        """
        try:
            # Get selected month/year from combo box
            month, year = self.month_year_combo.currentData()
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date()
            else:
                end_date = datetime(year, month + 1, 1).date()

            # Initialize calendar service
            SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "SERVICE_ACCOUNT_FILE.json")
            SCOPES = ['https://www.googleapis.com/auth/calendar']
            CALENDAR_ID = os.getenv("CALENDAR_ID")
            
            credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            service = build('calendar', 'v3', credentials=credentials)
            
            # Fetch events
            events_result = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=start_date.isoformat() + 'T00:00:00Z',
                timeMax=end_date.isoformat() + 'T00:00:00Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            customer_data = {}
            valid_clients = fetch_all_clients()
            full_event_list = []
            
            for event in events_result.get('items', []):
                title = event.get('summary', '').strip()
                matching_client = None
                for client in valid_clients:
                    if client in title:
                        matching_client = client
                        break
                if not title or not matching_client:
                    continue
                event['matched_client'] = matching_client
                full_event_list.append(event)

                # Always use only the matched client name for display
                display_name = matching_client

                # Get organizer username
                organizer = event.get('organizer', {}).get('email', '')
                username = organizer.split('@')[0] if organizer and '@' in organizer else ""
                
                # Calculate event duration in hours
                try:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    
                    if 'dateTime' in event['start']:
                        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                        duration = (end_dt - start_dt).total_seconds() / 3600
                    else:
                        duration = 8  # Default 8 hours for all-day events
                    
                    if display_name not in customer_data:
                        customer_data[display_name] = {'hours': 0, 'organizers': {}}
                    
                    customer_data[display_name]['hours'] += duration
                    if username:
                        if username not in customer_data[display_name]['organizers']:
                            customer_data[display_name]['organizers'][username] = 0
                        customer_data[display_name]['organizers'][username] += duration
                        
                except Exception as e:
                    print(f"Error processing event {title}: {e}")
            
            if full_events:
                return full_event_list
            return customer_data
            
        except Exception as e:
            print(f"Error fetching calendar events: {e}")
            return [] if full_events else {}

    def _create_instructors_map(self):
        """Create a mapping of email usernames to full instructor names"""
        instructors = fetch_instructors_from_google()
        email_to_name = {}
        for instructor in instructors:
            email = instructor.get('מייל', '').strip()
            if '@' in email:
                username = email.split('@')[0]
                email_to_name[username] = instructor.get('שם', username)
        return email_to_name

    def populate_billing_data(self):
        """Populate the billing table with data"""
        customer_data = self.get_current_month_events()
        
        self.table.setRowCount(len(customer_data))
        
        # Get current month and year for cell key generation
        month, year = self.month_year_combo.currentData()
        
        for row, (customer, data) in enumerate(customer_data.items()):
            # Customer name with larger purple font - ensure name appears first
            customer_item = QTableWidgetItem(customer)  # Only use the matched client name
            customer_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            font = customer_item.font()
            font.setPointSize(font.pointSize() + 2)
            customer_item.setFont(font)
            customer_item.setForeground(QColor("purple"))
            self.table.setItem(row, 0, customer_item)
            
            # Monthly hours with larger purple font
            hours_item = QTableWidgetItem(f"{data['hours']:.1f}")
            hours_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            hours_item.setFont(font)  # Reuse the same font from above
            hours_item.setForeground(QColor("purple"))
            self.table.setItem(row, 1, hours_item)
            
            # Convert usernames to full instructor names and calculate hours per instructor
            instructor_hours_map = {}
            for username in data['organizers']:
                full_name = self.instructors_map.get(username, username)
                if (full_name not in instructor_hours_map):
                    instructor_hours_map[full_name] = 0
                instructor_hours_map[full_name] += data['organizers'][username]
            
            # Create hours text for B1 column
            hours_text = "\n".join([f"{hours:.1f}" for name, hours in sorted(instructor_hours_map.items())])
            hours_b1_item = QTableWidgetItem(hours_text)
            hours_b1_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            hours_b1_item.setForeground(QColor("green"))
            self.table.setItem(row, 2, hours_b1_item)  # Column B1
            
            # Create instructor item with names only (column 3) - removed hours
            instructor_names = sorted([name for name in instructor_hours_map.keys()])
            instructor_text = "\n".join(instructor_names)
            instructor_item = QTableWidgetItem(instructor_text)
            instructor_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            instructor_item.setForeground(QColor("green"))
            self.table.setItem(row, 3, instructor_item)
            
            # Get cell-specific value for hourly rate (תמחור שעה) or use default 350
            hourly_rate_key = f"{customer}-{month}-{year}-תמחור שעה"
            hourly_rate = float(self.cell_values.get(hourly_rate_key, 350))
            
            # תמחור שעה column - make editable
            rate_item = QTableWidgetItem(f"{hourly_rate:.2f}")
            rate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rate_item.setForeground(QColor("black"))
            # Set flags to make item selectable and editable
            flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
            rate_item.setFlags(flags)
            self.table.setItem(row, 4, rate_item)
            
            # Get cell-specific value for discount (הנחה %) or use default 0
            discount_key = f"{customer}-{month}-{year}-הנחה %"
            discount = float(self.cell_values.get(discount_key, 0))
            
            # הנחה % column - make editable
            discount_item = QTableWidgetItem(f"{discount:.2f}")
            discount_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            discount_item.setForeground(QColor("black"))
            # Set flags to make item selectable and editable
            discount_item.setFlags(flags)
            self.table.setItem(row, 5, discount_item)
            
            # Calculate total (Hours * Rate * (1 - Discount/100))
            self.calculate_row_total(row)

            # Adjust row height based on number of instructors
            row_height = max(50, len(instructor_names) * 25)
            self.table.setRowHeight(row, row_height)

        # Set resizable לפי מדריך column
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        # Enable text wrapping for לפי מדריך and instructor columns
        for row in range(self.table.rowCount()):
            for col in [2, 3]:  # לפי מדריך and instructor columns
                cell_item = self.table.item(row, col)
                if cell_item:
                    cell_item.setFlags(cell_item.flags() | Qt.ItemFlag.ItemIsSelectable)
                    cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

    def calculate_row_total(self, row):
        """Calculate and update the total for a row"""
        try:
            # Get hours from סהכ שעות column
            hours_item = self.table.item(row, 1)
            if not hours_item:
                return
                
            # Get rate from תמחור שעה column
            rate_item = self.table.item(row, 4)
            if not rate_item:
                return
                
            # Get discount from הנחה % column
            discount_item = self.table.item(row, 5)
            if not discount_item:
                return
                
            # Parse values with proper error handling
            try:
                hours = float(hours_item.text())
                rate = float(rate_item.text())
                discount = float(discount_item.text())
            except ValueError:
                return
                
            # Calculate total: Hours * Rate * (1 - Discount/100)
            subtotal = hours * rate
            total = subtotal * (1 - discount / 100)
            
            # Format the total with 2 decimal places
            formatted_total = f"{total:.2f}"
            
            # Update or create the total item
            total_item = self.table.item(row, 6)
            if not total_item:
                total_item = QTableWidgetItem()
                self.table.setItem(row, 6, total_item)
                
            # Set the total text and formatting
            total_item.setText(formatted_total)
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Apply purple color and bold font
            font = total_item.font()
            font.setPointSize(font.pointSize() + 1)
            font.setBold(True)
            total_item.setFont(font)
            total_item.setForeground(QColor("purple"))
            
            # Make sure the total is not editable
            total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
        except Exception as e:
            print(f"Error calculating row total: {e}")

    def handle_cell_click(self, row, col):
        """Handle cell clicks for editable fields and client event popup"""
        client_item = self.table.item(row, 0)
        if not client_item:
            return
            
        client_name = client_item.text()
        month, year = self.month_year_combo.currentData()

        # לקוח column (show events popup)
        if col == 0:
            # Fetch this month's events for this client
            all_events = self.get_current_month_events(full_events=True)
            client_events = [
                e for e in all_events
                if e.get('matched_client', '') == client_name
            ]
            dlg = ClientEventsDialog(client_name, client_events, self.instructors_map, self)
            dlg.exec()
            return
            
        # Enable editing for תמחור שעה and הנחה % columns
        if col in [4, 5]:  # Columns for תמחור שעה and הנחה %
            # Temporarily block signals to prevent recursive calls
            self.table.blockSignals(True)
            # Start editing the item
            self.table.editItem(self.table.item(row, col))
            self.table.blockSignals(False)
            return
            
    def save_edited_cell(self, item):
        """Handle saving an edited cell's value"""
        if not item or item.column() not in [4, 5]:  # Only handle rate and discount columns
            return
            
        try:
            row = item.row()
            client_item = self.table.item(row, 0)
            if not client_item:
                return
                
            client_name = client_item.text()
            month, year = self.month_year_combo.currentData()
            
            # Determine column type and validate input
            if item.column() == 4:  # תמחור שעה
                column_type = "תמחור שעה"
                try:
                    value = float(item.text().replace(',', '.'))  # Handle both , and . as decimal separators
                    if value < 0:
                        raise ValueError("Value cannot be negative")
                    # Format with 2 decimal places
                    formatted_value = f"{value:.2f}"
                except ValueError:
                    QMessageBox.warning(self, "שגיאה", "אנא הזן מספר תקין")
                    item.setText("350.00")
                    return
            else:  # הנחה %
                column_type = "הנחה %"
                try:
                    value = float(item.text().replace(',', '.'))  # Handle both , and . as decimal separators
                    if value < 0 or value > 100:
                        raise ValueError("Value must be between 0 and 100")
                    # Format with 2 decimal places
                    formatted_value = f"{value:.2f}"
                except ValueError:
                    QMessageBox.warning(self, "שגיאה", "אנא הזן מספר בין 0 ל-100")
                    item.setText("0.00")
                    return
            
            # Update the cell with formatted value
            if item.text() != formatted_value:
                item.setText(formatted_value)
                return  # The textChanged signal will trigger another save_edited_cell
            
            # Save the value to Google Sheets
            self.save_cell_value(client_name, column_type, float(formatted_value))
            
            # Recalculate the total for this row
            self.calculate_row_total(row)
            
        except Exception as e:
            print(f"Error saving cell value: {e}")
            QMessageBox.warning(self, "שגיאה", f"אירעה שגיאה בשמירת הערך: {str(e)}")
            
    def handle_rate_cell_click(self, row, col, client_name, column_type):
        """Handle click for rate and discount cells"""
        item = self.table.item(row, col)
        current_value = item.text() if item else ("350" if column_type == "תמחור שעה" else "0")
        
        # Create centered input dialog
        input_dialog = QInputDialog(self)
        input_dialog.setInputMode(QInputDialog.InputMode.TextInput)
        input_dialog.setWindowTitle(column_type)
        
        # Set appropriate label text based on column type
        if column_type == "תמחור שעה":
            input_dialog.setLabelText("הזן תמחור שעה:")
        else:  # הנחה %
            input_dialog.setLabelText("הזן אחוז הנחה:")
            
        input_dialog.setTextValue(current_value)
        
        # Set all dialog elements to black font and color
        font = QFont("Arial", 16)
        input_dialog.setFont(font)
        input_dialog.setStyleSheet("""
            QInputDialog, QInputDialog QLabel, QInputDialog QLineEdit, QInputDialog QPushButton {
                color: black;
                font-family: Arial;
                font-size: 16px;
            }
        """)
        
        # Center align the text input
        line_edit = input_dialog.findChild(QLineEdit)
        if line_edit:
            line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            line_edit.setFont(font)
            line_edit.setStyleSheet("color: black; font-family: Arial; font-size: 16px;")
        
        # Set button font and color
        for btn in input_dialog.findChildren(QPushButton):
            btn.setFont(font)
            btn.setStyleSheet("color: black; font-family: Arial; font-size: 16px;")
        
        if input_dialog.exec():
            try:
                # Validate numeric input
                value = float(input_dialog.textValue())
                item.setText(str(value))
                
                # Save the value for this specific cell
                self.save_cell_value(client_name, column_type, value)
                
                # Recalculate the total
                self.calculate_row_total(row)
            except ValueError:
                QMessageBox.warning(self, "שגיאה", "אנא הזן מספר תקין")

    def go_back(self):
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            mw.setCentralWidget(Dashboard(mw))

    def export_to_sheets(self):
        """Export current billing data to Google Sheets with optimized batch operations."""
        try:
            # Get the month name and year for worksheet name
            month, year = self.month_year_combo.currentData()
            hebrew_months = [
                "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
            ]
            worksheet_name = f"{hebrew_months[month-1]} {year}"

            gc = get_gspread_client()
            spreadsheet_id = os.getenv("billing_SPREADSHEET_ID")
            if not spreadsheet_id:
                raise Exception("Missing billing_SPREADSHEET_ID in babisteps.env")
            sh = gc.open_by_key(spreadsheet_id)

            # Track if worksheet is new to determine if we need full update
            is_new_worksheet = False
            try:
                worksheet = sh.worksheet(worksheet_name)
                # Get existing data to compare with later
                existing_data = worksheet.get_all_values()
                if len(existing_data) == 0:
                    existing_data = [[""] * 7]  # Initialize with empty header row
            except:
                worksheet = sh.add_worksheet(worksheet_name, rows=100, cols=7)
                is_new_worksheet = True
                existing_data = [[""] * 7]  # Initialize with empty header row

            # Prepare headers and data
            headers = ["סיכום", "הנחה %", "תמחור שעה", "מדריך", "לפי מדריך", "סהכ שעות", "לקוח"]
            
            # Prepare all table data
            table_data = []
            for row in range(self.table.rowCount()):
                row_data = []
                for col in reversed(range(self.table.columnCount())):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else '')
                table_data.append(row_data)
            
            # Combine headers and data for one batch update
            all_data = [headers] + table_data
            
            # Calculate which rows to update
            rows_to_update = []
            if is_new_worksheet:
                # If it's a new worksheet, update everything
                rows_to_update = list(range(len(all_data)))
            else:
                # Compare with existing data and only update changed rows
                for i in range(len(all_data)):
                    if i >= len(existing_data) or all_data[i] != existing_data[i]:
                        rows_to_update.append(i)
            
            # Batch update only changed rows
            batch_updates = []
            
            # Always update header row
            if 0 in rows_to_update or is_new_worksheet:
                worksheet.update('A1:G1', [headers])
                
            # Update only changed data rows
            for row_idx in rows_to_update:
                if row_idx > 0:  # Skip header (already updated)
                    row_num = row_idx + 1  # 1-indexed for sheets
                    row_range = f'A{row_num}:G{row_num}'
                    worksheet.update(row_range, [all_data[row_idx]])
            
            # Apply formatting in batches by column
            format_requests = []
            
            # Header row formatting
            header_format = {
                'textFormat': {'bold': True, 'foregroundColor': {'red': 0, 'green': 0, 'blue': 1}},
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE'
            }
            
            # Column-specific formatting for the entire data range
            data_rows = len(all_data)
            if data_rows > 1:  # Only if we have data
                # Column formats (define once per column)
                column_formats = []
                
                # Columns: לקוח and סהכ שעות in purple
                purple_format = {
                    'textFormat': {'foregroundColor': {'red': 0.5, 'green': 0, 'blue': 0.5}},
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Columns: לפי מדריך and מדריך in green
                green_format = {
                    'textFormat': {'foregroundColor': {'red': 0, 'green': 0.5, 'blue': 0}},
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Columns: תמחור שעה and הנחה % in black
                black_format = {
                    'textFormat': {'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}},
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Column: סיכום in purple and bold
                summary_format = {
                    'textFormat': {
                        'foregroundColor': {'red': 0.5, 'green': 0, 'blue': 0.5},
                        'bold': True
                    },
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Apply header format
                worksheet.format('A1:G1', header_format)
                
                # Apply column formats
                if data_rows > 1:
                    data_range = f'A2:G{data_rows}'
                    
                    # Apply center alignment to all data cells
                    worksheet.format(data_range, {'horizontalAlignment': 'CENTER', 'verticalAlignment': 'MIDDLE'})
                    
                    # Format specific columns
                    worksheet.format(f'A2:A{data_rows}', summary_format)  # סיכום
                    worksheet.format(f'B2:C{data_rows}', black_format)    # הנחה % & תמחור שעה
                    worksheet.format(f'D2:E{data_rows}', green_format)    # מדריך & לפי מדריך
                    worksheet.format(f'F2:G{data_rows}', purple_format)   # סהכ שעות & לקוח
            
            # Show confirmation
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("הנתונים הועברו בהצלחה לגיליון אקסל")
            msg.setWindowTitle("ייצוא הושלם")
            msg.setStyleSheet("""
                QMessageBox { background-color: #f0f0f0; }
                QMessageBox QLabel { color: black; }
                QMessageBox QPushButton { color: black; padding: 5px 20px; }
            """)
            msg.exec()

        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בייצוא נתונים: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.go_back()
        super().keyPressEvent(event)
