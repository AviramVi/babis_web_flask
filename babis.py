from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QGridLayout,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QHBoxLayout, 
    QAbstractItemView, QMessageBox, QComboBox, QDialog, QDialogButtonBox, QLineEdit, 
    QTextEdit, QCheckBox  # Add QCheckBox here
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal, QPoint  # ← Add pyqtSignal here
from PyQt6.QtGui import QFont, QCursor, QColor, QPalette, QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QInputDialog
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import pytz

import sys
import os
from dotenv import load_dotenv
import gspread
import concurrent.futures
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QTextDocument

class DashboardCard(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFixedSize(312, 234)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #ADD8E6;
                border-radius: 24px;
                border: 3px solid #808080;
            }
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout = QVBoxLayout(self)
        label = QLabel(title, self)
        label.setFont(QFont("Arial", 31, QFont.Weight.Bold))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background: transparent; color: black;")
        layout.addWidget(label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def enterEvent(self, event):
        self.setStyleSheet("""
            QFrame {
                background-color: #90EE90;
                border-radius: 24px;
                border: 3px solid #808080;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("""
            QFrame {
                background-color: #ADD8E6;
                border-radius: 24px;
                border: 3px solid #808080;
            }
        """)
        super().leaveEvent(event)

# Global variable for gspread client
gspread_client = None

def get_gspread_client():
    global gspread_client
    if (gspread_client is not None):
        return gspread_client
    # Load env and use SERVICE_ACCOUNT_FILE.json for credentials
    env_path = os.path.join(os.path.dirname(__file__), "babisteps.env")
    load_dotenv(env_path)
    service_account_path = os.path.join(os.path.dirname(__file__), "SERVICE_ACCOUNT_FILE.json")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_file(service_account_path, scopes=scopes)
    gspread_client = gspread.authorize(credentials)
    return gspread_client

def fetch_instructors_from_google(force_refresh=False):
    # Try to get cache from MainWindow if available
    app = QApplication.instance()
    mw = app.activeWindow() if app else None
    if mw and hasattr(mw, 'instructors_cache') and mw.instructors_cache is not None and not force_refresh:
        return mw.instructors_cache
    gc = get_gspread_client()
    sheet_name = os.getenv("INSTRUCTORS_SHEET_NAME", "מדריכים")
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    if not spreadsheet_id:
        raise Exception("Missing SPREADSHEET_ID in babisteps.env")
    sh = gc.open_by_key(spreadsheet_id)
    worksheet = sh.worksheet(sheet_name)
    # Get all records to process
    records = worksheet.get_all_records()
    # Get raw data to access column F
    raw_data = worksheet.get_all_values()
    headers = raw_data[0]
    # Update each record with status from column F (index 5)
    for i, record in enumerate(records):
        if i + 1 < len(raw_data):  # +1 because records don't include header row
            row_data = raw_data[i + 1]
            if len(row_data) > 5:  # Make sure column F exists
                status_from_col_f = row_data[5].strip()
                # Set status based on column F
                if status_from_col_f == "לא פעיל":
                    record['סטטוס'] = "לא פעיל"
                else:
                    record['סטטוס'] = "פעיל"
    # Save to cache
    if mw and hasattr(mw, 'instructors_cache'):
        mw.instructors_cache = records
    return records

def fetch_all_clients(force_refresh=False):
    app = QApplication.instance()
    mw = app.activeWindow() if app else None
    if mw and hasattr(mw, 'clients_cache') and mw.clients_cache is not None and not force_refresh:
        return mw.clients_cache
    try:
        gc = get_gspread_client()
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        # Get private clients
        private_sheet = gc.open_by_key(spreadsheet_id).worksheet("לקוחות פרטיים")
        private_clients = [str(c['שם']) for c in private_sheet.get_all_records()]
        # Get institutional clients (using גוף as name)
        institutional_sheet = gc.open_by_key(spreadsheet_id).worksheet("לקוחות מוסדיים")
        institutional_clients = [str(c['גוף']) for c in institutional_sheet.get_all_records()]
        all_clients = set(private_clients + institutional_clients)
        # Save to cache
        if mw and hasattr(mw, 'clients_cache'):
            mw.clients_cache = all_clients
        return all_clients
    except Exception as e:
        print(f"Error fetching clients: {e}")
        return set()

class InstructorCardDialog(QDialog):
    def __init__(self, instructor, parent=None, is_new=False):
        super().__init__(parent)
        self.instructor = instructor
        self.is_new = is_new
        self.setWindowTitle(instructor.get('שם', ''))
        self.setFixedWidth(380)
        self.setStyleSheet("""
            QDialog {
                background: #d3d3d3;  # Changed to light grey
                border-radius: 24px;
                border: 2px solid #2196F3;
                padding: 24px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        # Helper for blue, centered field headers (match name color)
        def blue_label(text):
            lbl = QLabel(text, self)
            lbl.setFont(QFont("Arial", 17, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #2196F3; background: transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return lbl

        # Helper for centered QLineEdit, same size as header
        def centered_lineedit(val):
            le = QLineEdit(val, self)
            le.setFont(QFont("Arial", 17))
            le.setStyleSheet("color: black;")
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return le
            
        if is_new:
            # For new instructors, add name field first
            layout.addWidget(blue_label("שם"))
            self.name_edit = centered_lineedit('')
            layout.addWidget(self.name_edit)
        else:
            # Name (read-only) for existing instructors
            name = QLabel(instructor.get('שם', ''), self)
            name.setFont(QFont("Arial", 26, QFont.Weight.Bold))
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name.setStyleSheet("color: #2196F3; margin-bottom: 12px;")
            layout.addWidget(name)

        # Match table column names: ["שם", "טלפון", "מייל", "התמחויות", "הערות"]
        self.phone_edit = centered_lineedit(str(instructor.get('טלפון', '')))
        layout.addWidget(blue_label("טלפון"))
        layout.addWidget(self.phone_edit)

        self.mail_edit = centered_lineedit(str(instructor.get('מייל', '')))
        layout.addWidget(blue_label("מייל"))
        layout.addWidget(self.mail_edit)

        self.expertise_edit = centered_lineedit(str(instructor.get('התמחויות', '')))
        layout.addWidget(blue_label("התמחויות"))
        layout.addWidget(self.expertise_edit)

        self.notes_edit = QTextEdit(str(instructor.get('הערות', '')), self)
        self.notes_edit.setFont(QFont("Arial", 17))
        self.notes_edit.setStyleSheet("color: black;")
        self.notes_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notes_edit.setFixedHeight(self.notes_edit.fontMetrics().height() * 2 + 16)
        layout.addWidget(blue_label("הערות"))
        layout.addWidget(self.notes_edit)

        # Status (פעיל/לא פעיל) as a checkbox
        self.active_checkbox = QCheckBox("פעיל", self)
        self.active_checkbox.setFont(QFont("Arial", 14))
        self.active_checkbox.setStyleSheet("color: #2196F3;")
        self.active_checkbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.active_checkbox.setContentsMargins(0, 8, 0, 8)
        
        # Set checkbox status based on 'סטטוס' field (which is now set from column F)
        status = str(instructor.get('סטטוס', '')).strip()
        self.active_checkbox.setChecked(status != "לא פעיל")
        
        layout.addWidget(self.active_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)

        # Last update (עדכון אחרון)
        last_update_val = instructor.get('עדכון אחרון', '')
        if last_update_val:
            last_update = QLabel(f"עדכון אחרון: {last_update_val}", self)
            last_update.setFont(QFont("Arial", 13))
            last_update.setStyleSheet("color: #2196F3; background: transparent;")
            last_update.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(last_update)

        layout.addStretch(1)

        # OK button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet(
            "color: white; background: #2196F3; border-radius: 8px; padding: 8px 24px; font-weight: bold;"
        )
        buttons.setCenterButtons(True)
        buttons.accepted.connect(self.on_accept)
        layout.addWidget(buttons, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def on_accept(self):
        if self.is_new:
            # Get name for new instructor
            new_name = self.name_edit.text().strip()
            if not new_name:
                QMessageBox.critical(self, "שגיאה", "חובה להזין שם למדריך")
                return
            self.instructor['שם'] = new_name

        # Gather new values
        new_phone = self.phone_edit.text().strip()
        new_mail = self.mail_edit.text().strip()
        new_expertise = self.expertise_edit.text().strip()
        new_notes = self.notes_edit.toPlainText().strip()
        new_status = "פעיל" if self.active_checkbox.isChecked() else "לא פעיל"

        # Track changes
        changed = False
        updates = {}

        if self.instructor.get('טלפון', '').strip() != new_phone:
            updates['טלפון'] = new_phone
            self.instructor['טלפון'] = new_phone
            changed = True
        if self.instructor.get('מייל', '').strip() != new_mail:
            updates['מייל'] = new_mail
            self.instructor['מייל'] = new_mail
            changed = True
        if self.instructor.get('התמחויות', '').strip() != new_expertise:
            updates['התמחויות'] = new_expertise
            self.instructor['התמחויות'] = new_expertise
            changed = True
        if self.instructor.get('הערות', '').strip() != new_notes:
            updates['הערות'] = new_notes
            self.instructor['הערות'] = new_notes
            changed = True
        if self.instructor.get('סטטוס', '').strip() != new_status:
            updates['סטטוס'] = new_status
            self.instructor['סטטוס'] = new_status
            changed = True

        if changed or self.is_new:
            try:
                if self.is_new:
                    self.add_instructor_to_sheet()
                else:
                    self.update_instructor_in_sheet(updates)
            except Exception as e:
                QMessageBox.critical(self, "שגיאה", f"שגיאה בעדכון מדריך: {e}")
        self.accept()

    def update_instructor_in_sheet(self, updates):
        # Find the instructor row in the sheet and update the changed fields
        gc = get_gspread_client()
        sheet_name = os.getenv("INSTRUCTORS_SHEET_NAME", "מדריכים")
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet(sheet_name)
        all_records = worksheet.get_all_records()
        for idx, record in enumerate(all_records):
            if (
                str(record.get('שם', '')).strip() == str(self.instructor.get('שם', '')).strip()
            ):
                headers = worksheet.row_values(1)
                for field, value in updates.items():
                    if field in headers:
                        col_idx = headers.index(field) + 1
                        worksheet.update_cell(idx + 2, col_idx, value)
                
                # If status was changed to "לא פעיל", also write it to column F
                if 'סטטוס' in updates and updates['סטטוס'] == 'לא פעיל':
                    # Column F is the 6th column (index 5 + 1 for gspread's 1-based indexing)
                    worksheet.update_cell(idx + 2, 6, 'לא פעיל')
                    
                    # Format the entire row with grey font
                    row_num = idx + 2
                    num_cols = len(headers)
                    cell_range = f'A{row_num}:{chr(65 + num_cols - 1)}{row_num}'  # A2:Z2 format
                    worksheet.format(cell_range, {
                        "textFormat": {
                            "foregroundColor": {
                                "red": 0.5,
                                "green": 0.5,
                                "blue": 0.5
                            }
                        }
                    })
                    
                # If status was changed to "פעיל", clear column F
                elif 'סטטוס' in updates and updates['סטטוס'] == 'פעיל':
                    worksheet.update_cell(idx + 2, 6, '')
                    
                    # Reset the entire row to black font
                    row_num = idx + 2
                    num_cols = len(headers)
                    cell_range = f'A{row_num}:{chr(65 + num_cols - 1)}{row_num}'
                    worksheet.format(cell_range, {
                        "textFormat": {
                            "foregroundColor": {
                                "red": 0,
                                "green": 0,
                                "blue": 0
                            }
                        }
                    })
                break

    def add_instructor_to_sheet(self):
        """Add new instructor to the first empty row in the worksheet"""
        gc = get_gspread_client()
        sheet_name = os.getenv("INSTRUCTORS_SHEET_NAME", "מדריכים")
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        sh = gc.open_by_key(spreadsheet_id)
        
        # Initialize worksheet
        worksheet = sh.worksheet(sheet_name)  # Add this line to define `worksheet`
        
        # Get all current instructors to find first empty row
        all_records = worksheet.get_all_records()
        next_row = len(all_records) + 2  # +2 for header row and 1-based indexing
        
        # Get headers to ensure correct column order
        headers = worksheet.row_values(1)
        
        # Create row values in the correct order
        row_values = []
        for header in headers:
            if header == 'עדכון אחרון':
                row_values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            else:
                row_values.append(self.instructor.get(header, ''))
        
        # Add the new row
        worksheet.insert_row(row_values, next_row)
        
        # If instructor status is "לא פעיל", also write to column F
        if self.instructor.get('סטטוס', '') == 'לא פעיל':
            worksheet.update_cell(next_row, 6, 'לא פעיל')  # Column F is 6
            
            # Format the entire row with grey font
            num_cols = len(headers)
            cell_range = f'A{next_row}:{chr(65 + num_cols - 1)}{next_row}'
            worksheet.format(cell_range, {
                "textFormat": {
                    "foregroundColor": {
                        "red": 0.5,
                        "green": 0.5,
                        "blue": 0.5
                    }
                }
            })

class ResizableTable(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = self.viewport().width()
        
        # Fixed column widths in proportion
        col_widths = [
            int(width * 0.15),  # שם/איש קשר
            int(width * 0.15),  # טלפון
            int(width * 0.15),  # מייל
            int(width * 0.15),  # התמחויות
            int(width * 0.4)    # הערות
        ]
        
        for col, width in enumerate(col_widths):
            self.setColumnWidth(col, width)

class EmailTableItem(QTableWidgetItem):
    def __init__(self, email):
        super().__init__(email)
        self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        # Make it look like a link
        self.setForeground(QColor("blue"))
        font = self.font()
        font.setUnderline(True)
        self.setFont(font)

class PhoneTableItem(QTableWidgetItem):
    def __init__(self, phone):
        super().__init__(phone)
        self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        # Make it look like a link in purple
        self.setForeground(QColor("purple"))
        font = self.font()
        font.setUnderline(True)
        self.setFont(font)

class InstructorScreen(QWidget):
    def __init__(self, parent=None, instructors=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #d3d3d3;")
        main_layout = QVBoxLayout(self)
        header = QLabel("מדריכים", self)
        header.setFont(QFont("Arial", int(40 * 1.3), QFont.Weight.Bold))  # 30% larger
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: blue; background: transparent;")
        main_layout.addWidget(header)

        # Add top controls layout
        top_controls = QHBoxLayout()
        
        # Add instructor button
        add_btn = QPushButton("הוספת מדריך", self)
        add_btn.setFixedWidth(120)
        add_btn.setFont(QFont("Arial", int(14 * 1.3)))
        add_btn.setStyleSheet("""
            QPushButton {
                color: black;
                background-color: #90EE90;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #98FB98;
            }
        """)
        add_btn.clicked.connect(self.add_new_instructor)
        top_controls.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        top_controls.addStretch()  # Push button to the left
        main_layout.addLayout(top_controls)

        # Table
        self.table = ResizableTable(self)
        header_font_size = int(17 * 1.3)
        header_style = f"QHeaderView::section {{ color: blue; font-weight: bold; font-family: Arial; font-size: {header_font_size}px; }}"
        self.table.horizontalHeader().setStyleSheet(header_style)
        self.table.verticalHeader().setStyleSheet(header_style)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["שם", "טלפון", "מייל", "התמחויות", "הערות"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        # Enable bidirectional sorting
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().sortIndicatorChanged.connect(self.handle_sort)
        self.table.cellClicked.connect(self.show_instructor_card)
        default_height = self.table.verticalHeader().defaultSectionSize()
        self.table.verticalHeader().setDefaultSectionSize(int(default_height * 1.3 * 1.3))
        main_layout.addWidget(self.table)

        # Back button
        self.back_btn = QPushButton("חזרה", self)
        self.back_btn.setFixedWidth(120)
        self.back_btn.setFont(QFont("Arial", int(14 * 1.3)))
        self.back_btn.setStyleSheet("color: black;")
        self.back_btn.clicked.connect(self.go_back)
        main_layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.setLayout(main_layout)
        self.instructors = instructors if instructors is not None else []
        if not self.instructors:
            self.load_instructors()
        else:
            self.populate_table()

    # Replace sort_table with handle_sort
    def handle_sort(self, column, order):
        self.table.sortItems(column, Qt.SortOrder(order))
        self.update_sorted_row_indices()
        
    # Remove the sort_table method as it's no longer needed

    def load_instructors(self):
        try:
            self.instructors = fetch_instructors_from_google()
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בטעינת מדריכים: {e}")

    def populate_table(self):
        self.table.setRowCount(len(self.instructors))
        self.sorted_row_indices = list(range(len(self.instructors)))  # Reset mapping

        # Sort instructors - active ones first, then inactive ones
        active_instructors = []
        inactive_instructors = []
        for instructor in self.instructors:
            if str(instructor.get('סטטוס', '')).strip() == "לא פעיל":
                inactive_instructors.append(instructor)
            else:
                active_instructors.append(instructor)

        # Populate table with active instructors first
        row = 0
        font = QFont("Arial", int(17 * 1.3 * 0.9))  # regular font
        for instructor in active_instructors + inactive_instructors:
            is_inactive = str(instructor.get('סטטוס', '')).strip() == "לא פעיל"
            color = QColor("gray") if is_inactive else QColor("black")

            name_item = QTableWidgetItem(str(instructor.get('שם', '')))
            phone_item = PhoneTableItem(str(instructor.get('טלפון', '')))
            mail_item = EmailTableItem(str(instructor.get('מייל', '')))
            expertise_item = QTableWidgetItem(str(instructor.get('התמחויות', '')))
            notes_item = QTableWidgetItem(str(instructor.get('הערות', '')))

            # Set font color, background and alignment for all non-email items
            for item in [name_item, expertise_item, notes_item]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(color)
                item.setFont(font)
                if is_inactive:
                    item.setBackground(QColor("#e0e0e0"))
                item.setData(Qt.ItemDataRole.UserRole, is_inactive)

            # Set font and alignment for phone
            phone_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            phone_item.setFont(font)

            # Special handling for email - smaller font
            mail_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            smaller_font = QFont("Arial", int(17 * 1.3 * 0.9) - 2)  # 2px smaller
            mail_item.setFont(smaller_font)
            if is_inactive:
                mail_item.setBackground(QColor("#e0e0e0"))

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, phone_item)
            self.table.setItem(row, 2, mail_item)
            self.table.setItem(row, 3, expertise_item)
            self.table.setItem(row, 4, notes_item)
            row += 1

        # Disable default sorting to prevent mixing active/inactive
        self.table.setSortingEnabled(False)
        self.update_sorted_row_indices()

    def update_sorted_row_indices(self):
        # Map the current table row order to the original instructor list
        row_map = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)  # Name column
            if item is None:
                continue
            name = item.text()
            mail_item = self.table.item(row, 2)  # Email is now in column 2
            if mail_item is None:
                continue
            mail = mail_item.text()

            # Find the matching instructor in the original list
            for idx, instructor in enumerate(self.instructors):
                if (
                    str(instructor.get('שם', '')) == name and
                    str(instructor.get('מייל', '')) == mail
                ):
                    row_map.append(idx)
                    break
            else:
                row_map.append(-1)  # Should not happen
        self.sorted_row_indices = row_map

    def show_instructor_card(self, row, col):
        # Handle phone click for WhatsApp
        if (col == 1):  # Phone is now in column 1
            phone = self.table.item(row, col).text().strip()
            # Remove any non-digit characters
            phone = ''.join(filter(str.isdigit, phone))
            if phone:
                QDesktopServices.openUrl(QUrl(f"https://wa.me/972{phone[1:]}"))
            return
            
        # Handle email click 
        if (col == 2):  # Email is now in column 2
            email = self.table.item(row, col).text()
            QDesktopServices.openUrl(QUrl(f"mailto:{email}"))
            return

        # Regular card handling
        if hasattr(self, 'sorted_row_indices') and row < len(self.sorted_row_indices):
            instructor_idx = self.sorted_row_indices[row]
            if instructor_idx != -1:
                instructor = self.instructors[instructor_idx]
            else:
                instructor = self.instructors[row]
        else:
            instructor = self.instructors[row]
        dlg = InstructorCardDialog(instructor, self)
        if dlg.exec():  # If dialog was accepted
            self.populate_table()  # Refresh the table to show updated status

    def mousePressEvent(self, event):
        item = self.table.itemAt(self.table.viewport().mapFrom(self, event.pos()))
        if item and isinstance(item, EmailTableItem):
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(f"mailto:{item.text()}"))
        else:
            super().mousePressEvent(event)

    def go_back(self):
        mw = self.window()
        # Always create a new Dashboard instance, but preserve instructors_cache if possible
        if hasattr(mw, 'setCentralWidget'):
            new_dashboard = Dashboard(mw)
            # Preserve instructors_cache if coming from Dashboard
            if hasattr(mw, 'dashboard') and hasattr(mw.dashboard, 'instructors_cache'):
                new_dashboard.instructors_cache = mw.dashboard.instructors_cache
            # Or, if coming from InstructorScreen, preserve from self
            elif hasattr(self, 'instructors'):
                new_dashboard.instructors_cache = self.instructors
            mw.dashboard = new_dashboard
            mw.setCentralWidget(mw.dashboard)

    def add_new_instructor(self):
        """Create and show dialog for new instructor"""
        # Create empty instructor data
        new_instructor = {
            'שם': '',
            'טלפון': '',
            'מייל': '',
            'התמחויות': '',
            'הערות': '',
            'סטטוס': 'פעיל',
            'עדכון אחרון': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        dlg = InstructorCardDialog(new_instructor, self, is_new=True)
        if dlg.exec():
            self.instructors.append(new_instructor)
            self.populate_table()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.go_back()
        super().keyPressEvent(event)

class PrivateClientCardDialog(QDialog):
    def __init__(self, client, headers, parent=None):
        super().__init__(parent)
        self.client = client
        self.headers = headers
        self.setWindowTitle(client.get(headers[0], ''))
        self.setFixedWidth(380)
        self.setStyleSheet("""
            QDialog {
                background: #d3d3d3;  # Changed to light grey
                border-radius: 24px;
                border: 2px solid #2196F3;
                padding: 24px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        def blue_label(text):
            lbl = QLabel(text, self)
            lbl.setFont(QFont("Arial", 17, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #2196F3; background: transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return lbl

        def centered_lineedit(val):
            le = QLineEdit(val, self)
            le.setFont(QFont("Arial", 17))
            le.setStyleSheet("color: black;")
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return le

        def centered_textedit(val):
            te = QTextEdit(val, self)
            te.setFont(QFont("Arial", 17))
            te.setStyleSheet("color: black;")
            te.setAlignment(Qt.AlignmentFlag.AlignCenter)
            te.setFixedHeight(te.fontMetrics().height() * 2 + 16)
            return te

        # Name (editable)
        layout.addWidget(blue_label(headers[0]))
        self.name_edit = centered_lineedit(client.get(headers[0], ''))
        layout.addWidget(self.name_edit)

        self.edits = {}
        for idx, header in enumerate(headers[1:]):
            layout.addWidget(blue_label(header))
            if "הערה" in header or "הערות" in header:
                edit = centered_textedit(str(client.get(header, "")))
            else:
                edit = centered_lineedit(str(client.get(header, "")))
            layout.addWidget(edit)
            self.edits[header] = edit

        # Add Status (פעיל/לא פעיל) checkbox before the buttons
        self.active_checkbox = QCheckBox("פעיל", self)
        self.active_checkbox.setFont(QFont("Arial", 14))
        self.active_checkbox.setStyleSheet("color: #2196F3;")
        self.active_checkbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.active_checkbox.setContentsMargins(0, 8, 0, 8)
        status = str(client.get('סטטוס', '')).strip()
        self.active_checkbox.setChecked(status != "לא פעיל")
        layout.addWidget(self.active_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet(
            "color: white; background: #2196F3; border-radius: 8px; padding: 8px 24px; font-weight: bold;"
        )
        buttons.setCenterButtons(True)
        buttons.accepted.connect(self.on_accept)
        layout.addWidget(buttons, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def on_accept(self):
        new_name = self.name_edit.text().strip()
        if not new_name:
            QMessageBox.critical(self, "שגיאה", "חובה להזין שם ללקוח")
            return
        self.client[self.headers[0]] = new_name

        changed = False
        updates = {}
        for header, edit in self.edits.items():
            new_val = edit.toPlainText().strip() if isinstance(edit, QTextEdit) else edit.text().strip()
            if self.client.get(header, '').strip() != new_val:
                updates[header] = new_val
                self.client[header] = new_val
                changed = True

        # Add status to updates
        new_status = "פעיל" if self.active_checkbox.isChecked() else "לא פעיל"
        if self.client.get('סטטוס', '').strip() != new_status:
            updates['סטטוס'] = new_status
            self.client['סטטוס'] = new_status
            changed = True

        if changed:
            try:
                self.update_client_in_sheet(updates)
            except Exception as e:
                QMessageBox.critical(self, "שגיאה", f"שגיאה בעדכון לקוח: {e}")
        self.accept()

    def update_client_in_sheet(self, updates):
        gc = get_gspread_client()
        sheet_name = "לקוחות פרטיים"
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet(sheet_name)
        all_records = worksheet.get_all_records()
        # Find the row by the first column (usually name)
        for idx, record in enumerate(all_records):
            if str(record.get(self.headers[0], '')).strip() == str(self.client.get(self.headers[0], '')).strip():
                headers = worksheet.row_values(1)
                # Swap טלפון and מייל if needed to match table order
                if "טלפון" in headers and "מייל" in headers:
                    phone_idx = headers.index("טלפון")
                    mail_idx = headers.index("מייל")
                    if phone_idx > mail_idx:
                        headers[phone_idx], headers[mail_idx] = headers[mail_idx], headers[phone_idx]
                for field, value in updates.items():
                    if field in headers:
                        col_idx = headers.index(field) + 1
                        worksheet.update_cell(idx + 2, col_idx, value)
                
                # If status was changed to "לא פעיל", also write it to column F
                if 'סטטוס' in updates and updates['סטטוס'] == 'לא פעיל':
                    # Column F is the 6th column (index 5 + 1 for gspread's 1-based indexing)
                    worksheet.update_cell(idx + 2, 6, 'לא פעיל')
                    
                    # Format the entire row with grey font
                    row_num = idx + 2
                    num_cols = len(headers)
                    cell_range = f'A{row_num}:{chr(65 + num_cols - 1)}{row_num}'
                    worksheet.format(cell_range, {
                        "textFormat": {
                            "foregroundColor": {
                                "red": 0.5,
                                "green": 0.5,
                                "blue": 0.5
                            }
                        }
                    })
                    
                # If status was changed to "פעיל", clear column F
                elif 'סטטוס' in updates and updates['סטטוס'] == 'פעיל':
                    worksheet.update_cell(idx + 2, 6, '')
                    
                    # Reset the entire row to black font
                    row_num = idx + 2
                    num_cols = len(headers)
                    cell_range = f'A{row_num}:{chr(65 + num_cols - 1)}{row_num}'
                    worksheet.format(cell_range, {
                        "textFormat": {
                            "foregroundColor": {
                                "red": 0,
                                "green": 0,
                                "blue": 0
                            }
                        }
                    })
                break

class PrivateClientsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #d3d3d3;")
        main_layout = QVBoxLayout(self)
        header = QLabel("לקוחות פרטיים", self)
        header.setFont(QFont("Arial", int(40 * 1.3), QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: blue; background: transparent;")
        main_layout.addWidget(header)

        # Add top controls layout
        top_controls = QHBoxLayout()

        # Add client button
        add_btn = QPushButton("הוספת לקוח", self)
        add_btn.setFixedWidth(120)
        add_btn.setFont(QFont("Arial", int(14 * 1.3)))
        add_btn.setStyleSheet("""
            QPushButton {
                color: black;
                background-color: #90EE90;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #98FB98;
            }
        """)
        add_btn.clicked.connect(self.add_new_client)
        top_controls.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        top_controls.addStretch()  # Push button to the left
        main_layout.addLayout(top_controls)

        # Table
        self.table = ResizableTable(self)
        header_font_size = int(17 * 1.3)
        header_style = f"QHeaderView::section {{ color: blue; font-weight: bold; font-family: Arial; font-size: {header_font_size}px; }}"
        self.table.horizontalHeader().setStyleSheet(header_style)
        self.table.verticalHeader().setStyleSheet(header_style)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        # Enable bidirectional sorting
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().sortIndicatorChanged.connect(self.handle_sort)
        self.table.cellClicked.connect(self.show_client_card)
        default_height = self.table.verticalHeader().defaultSectionSize()
        self.table.verticalHeader().setDefaultSectionSize(int(default_height * 1.3 * 1.3 * 1.3))
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

        main_layout.addLayout(bottom_buttons)

        self.setLayout(main_layout)
        self.headers = []
        self.clients = []
        self.sorted_row_indices = []
        self.load_clients()

    def handle_sort(self, column, order):
        self.table.sortItems(column, Qt.SortOrder(order))
        self.update_sorted_row_indices()

    def load_clients(self):
        try:
            gc = get_gspread_client()
            sheet_name = "לקוחות פרטיים"
            spreadsheet_id = os.getenv("SPREADSHEET_ID")
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(sheet_name)
            # Fetch headers from A1-E1
            headers = worksheet.row_values(1)[:5]
            # Swap "טלפון" and "מייל" if both exist
            if "טלפון" in headers and "מייל" in headers:
                phone_idx = headers.index("טלפון")
                mail_idx = headers.index("מייל")
                headers[phone_idx], headers[mail_idx] = headers[mail_idx], headers[phone_idx]
            self.headers = headers
            self.table.setColumnCount(len(self.headers))
            self.table.setHorizontalHeaderLabels(self.headers)
            
            # Fetch all records
            self.clients = worksheet.get_all_records()
            
            # Get raw data to access column F for status
            raw_data = worksheet.get_all_values()
            
            # Update each record with status from column F (index 5)
            for i, record in enumerate(self.clients):
                if i + 1 < len(raw_data):  # +1 because records don't include header row
                    row_data = raw_data[i + 1]
                    if len(row_data) > 5:  # Make sure column F exists
                        status_from_col_f = row_data[5].strip()
                        # Set status based on column F
                        if status_from_col_f == "לא פעיל":
                            record['סטטוס'] = "לא פעיל"
                        else:
                            record['סטטוס'] = "פעיל"
            
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בטעינת לקוחות פרטיים: {e}")

    def populate_table(self):
        self.table.setRowCount(len(self.clients))
        self.sorted_row_indices = list(range(len(self.clients)))
        font = QFont("Arial", int(17 * 1.3 * 0.9))
        
        # Sort clients - active first, then inactive ones
        active_clients = []
        inactive_clients = []
        for client in self.clients:
            if str(client.get('סטטוס', '')).strip() == "לא פעיל":
                inactive_clients.append(client)
            else:
                active_clients.append(client)
        
        row = 0
        for client in active_clients + inactive_clients:
            is_inactive = str(client.get('סטטוס', '')).strip() == "לא פעיל"
            color = QColor("gray") if is_inactive else QColor("black")

            for col, header in enumerate(self.headers):
                value = str(client.get(header, ''))
                # Email/Phone columns: use special items
                if header == "מייל":
                    item = EmailTableItem(value)
                    item.setFont(font)
                    if is_inactive:
                        item.setBackground(QColor("#e0e0e0"))
                elif header == "טלפון":
                    item = PhoneTableItem(value)
                    item.setFont(font)
                    if is_inactive:
                        item.setBackground(QColor("#e0e0e0"))
                else:
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFont(font)
                    item.setForeground(color)
                    if is_inactive:
                        item.setBackground(QColor("#e0e0e0"))
                    
                item.setData(Qt.ItemDataRole.UserRole, is_inactive)
                self.table.setItem(row, col, item)
            row += 1

        self.table.setSortingEnabled(False)
        self.update_sorted_row_indices()

    def update_sorted_row_indices(self):
        row_map = []
        for row in range(self.table.rowCount()):
            first_col_item = self.table.item(row, 0)
            if first_col_item is None:
                continue
            first_col_val = first_col_item.text()
            # Try to match by first column value (usually name)
            for idx, client in enumerate(self.clients):
                if str(client.get(self.headers[0], '')) == first_col_val:
                    row_map.append(idx)
                    break
            else:
                row_map.append(-1)
        self.sorted_row_indices = row_map

    def show_client_card(self, row, col):
        # Email/Phone click functionality
        if self.headers:
            header = self.headers[col]
            item = self.table.item(row, col)
            if header == "טלפון":
                phone = item.text().strip()
                phone = ''.join(filter(str.isdigit, phone))
                if phone:
                    QDesktopServices.openUrl(QUrl(f"https://wa.me/972{phone[1:]}"))
                return
            if header == "מייל":
                email = item.text()
                QDesktopServices.openUrl(QUrl(f"mailto:{email}"))
                return
        # Show dialog for editing/viewing client details
        if hasattr(self, 'sorted_row_indices') and row < len(self.sorted_row_indices):
            client_idx = self.sorted_row_indices[row]
            if client_idx != -1:
                client = self.clients[client_idx]
            else:
                client = self.clients[row]
        else:
            client = self.clients[row]
        dlg = PrivateClientCardDialog(client, self.headers, self)
        if dlg.exec():
            self.populate_table()  # Refresh table if edited

    def mousePressEvent(self, event):
        item = self.table.itemAt(self.table.viewport().mapFrom(self, event.pos()))
        if item and isinstance(item, EmailTableItem):
            QDesktopServices.openUrl(QUrl(f"mailto:{item.text()}"))
        elif item and isinstance(item, PhoneTableItem):
            phone = item.text().strip()
            phone = ''.join(filter(str.isdigit, phone))
            if phone:
                QDesktopServices.openUrl(QUrl(f"https://wa.me/972{phone[1:]}"))
        else:
            super().mousePressEvent(event)

    def go_back(self):
        """Return to dashboard."""
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            mw.setCentralWidget(Dashboard(mw))

    def add_new_client(self):
        """Create and show dialog for new client"""
        # Create empty client data
        new_client = {header: '' for header in self.headers}
        new_client['סטטוס'] = 'פעיל'
        dlg = PrivateClientCardDialog(new_client, self.headers, self)
        if dlg.exec():
            self.clients.append(new_client)
            self.add_client_to_sheet(new_client)
            self.populate_table()

    def add_client_to_sheet(self, client):
        """Add new client to the first empty row in the worksheet"""
        try:
            gc = get_gspread_client()
            sheet_name = "לקוחות פרטיים"  # <-- Fixed: write to 'לקוחות פרטיים'
            spreadsheet_id = os.getenv("SPREADSHEET_ID")
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(sheet_name)

            # Get all current clients to find the first empty row
            all_records = worksheet.get_all_records()
            next_row = len(all_records) + 2  # +2 for header row and 1-based indexing

            # Get headers to ensure correct column order
            headers = worksheet.row_values(1)

            # Create row values in the correct order
            row_values = []
            for header in headers:
                row_values.append(client.get(header, ''))

            # Add the new row
            worksheet.insert_row(row_values, next_row)
            
            # If client status is "לא פעיל", also write to column F
            if client.get('סטטוס', '') == 'לא פעיל':
                worksheet.update_cell(next_row, 6, 'לא פעיל')  # Column F is 6
                
                # Format the entire row with grey font
                num_cols = len(headers)
                cell_range = f'A{next_row}:{chr(65 + num_cols - 1)}{next_row}'
                worksheet.format(cell_range, {
                    "textFormat": {
                        "foregroundColor": {
                            "red": 0.5,
                            "green": 0.5,
                            "blue": 0.5
                        }
                    }
                })
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בהוספת לקוח: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.go_back()
        super().keyPressEvent(event)

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
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.cellClicked.connect(self.handle_cell_click)
        self.table.setColumnCount(7)  # Changed from 6 to 7
        self.table.setHorizontalHeaderLabels(["לקוח", "סהכ שעות", "לפי מדריך", "מדריך", "תמחור שעה", "הנחה %", "סיכום"])
        self.table.setStyleSheet("""
            QTableView {
                selection-background-color: #ADD8E6;
            }
            QTableView::item:hover {
                background-color: #ADD8E6;
            }
        """)
        default_height = self.table.verticalHeader().defaultSectionSize()
        self.table.verticalHeader().setDefaultSectionSize(int(default_height * 1.3 * 1.3))
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

        # Connect export button
        self.export_btn.clicked.connect(self.export_to_sheets)

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
            
            # Get cell-specific value for hourly rate (תמחור שעה) or use default
            hourly_rate_key = f"{customer}-{month}-{year}-תמחור שעה"
            hourly_rate = self.cell_values.get(hourly_rate_key, 350)
            
            # תמחור שעה column
            rate_item = QTableWidgetItem(str(hourly_rate))
            rate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rate_item.setForeground(QColor("black"))
            self.table.setItem(row, 4, rate_item)
            
            # Get cell-specific value for discount (הנחה %) or use default
            discount_key = f"{customer}-{month}-{year}-הנחה %"
            discount = self.cell_values.get(discount_key, 0)
            
            # הנחה % column
            discount_item = QTableWidgetItem(str(discount))
            discount_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            discount_item.setForeground(QColor("black"))
            self.table.setItem(row, 5, discount_item)
            
            # Calculate total
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
            hours = float(self.table.item(row, 1).text())  # Get hours from סהכ שעות column
            rate = float(self.table.item(row, 4).text())   # Get rate from תמחור שעה column
            discount = float(self.table.item(row, 5).text())
            
            subtotal = hours * rate
            total = subtotal - (subtotal * discount / 100)
            
            # Create total item with purple font and bold
            total_item = QTableWidgetItem(f"{total:.2f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            font = total_item.font()
            font.setPointSize(font.pointSize() + 1)
            font.setBold(True)
            total_item.setFont(font)
            total_item.setForeground(QColor("purple"))
            self.table.setItem(row, 6, total_item)
        except:
            pass

    def handle_cell_click(self, row, col):
        """Handle cell clicks for editable fields and client event popup"""
        client_item = self.table.item(row, 0)
        if not client_item:
            return
        client_name = client_item.text()

        # לקוח column (show events popup)
        if col == 0:
            # Fetch this month's events for this client
            month, year = self.month_year_combo.currentData()
            all_events = self.get_current_month_events(full_events=True)
            client_events = [
                e for e in all_events
                if e.get('matched_client', '') == client_name
            ]
            dlg = ClientEventsDialog(client_name, client_events, self.instructors_map, self)
            dlg.exec()
            return

        # תמחור שעה column
        if col == 4:
            self.handle_rate_cell_click(row, col, client_name, "תמחור שעה")
        
        # הנחה % column
        if col == 5:
            self.handle_rate_cell_click(row, col, client_name, "הנחה %")
            
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

            # Prepare headers and data - in the order they appear in the table
            headers = ["לקוח", "סהכ שעות", "לפי מדריך", "מדריך", "תמחור שעה", "הנחה %", "סיכום"]
            
            # Prepare all table data
            table_data = []
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item is not None:
                        # Convert numbers to float when appropriate, keep as string otherwise
                        text = item.text()
                        if col in [1, 4, 5, 6]:  # Columns with numbers: סהכ שעות, תמחור שעה, הנחה %, סיכום
                            try:
                                # Remove any thousands separators and convert to float
                                clean_text = text.replace(',', '').replace('₪', '').strip()
                                if clean_text:  # Only convert if not empty string
                                    num = float(clean_text)
                                    # Keep as string but ensure proper decimal format
                                    row_data.append(str(int(num)) if num.is_integer() else str(num))
                                else:
                                    row_data.append('')
                            except (ValueError, AttributeError):
                                row_data.append(text)
                        else:
                            row_data.append(text)
                    else:
                        row_data.append('')
                table_data.append(row_data)
            
            # Combine headers and data for one batch update
            all_data = [headers] + table_data
            
            # Always update all data at once for consistency
            if all_data:
                # Clear existing data first
                worksheet.clear()
                
                # Update all data in one batch
                worksheet.update('A1', all_data, value_input_option='USER_ENTERED')
                
                # Set the header row format
                header_format = {
                    'textFormat': {'bold': True, 'foregroundColor': {'red': 0, 'green': 0, 'blue': 1}},
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                worksheet.format('A1:G1', header_format)
            
            # Apply number formatting to numeric columns
            data_rows = len(all_data)
            if data_rows > 1:  # Only if we have data
                # Format numbers with 2 decimal places
                number_format = {
                    'numberFormat': {
                        'type': 'NUMBER',
                        'pattern': '#,##0.00'
                    },
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Format percentage with 2 decimal places
                percent_format = {
                    'numberFormat': {
                        'type': 'PERCENT',
                        'pattern': '0.00%'
                    },
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Format summary column (column A)
                summary_format = {
                    'textFormat': {
                        'bold': True,
                        'foregroundColor': {'red': 0.5, 'green': 0, 'blue': 0.5}
                    },
                    'numberFormat': {
                        'type': 'NUMBER',
                        'pattern': '#,##0.00'
                    },
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Apply number formatting to numeric columns
                worksheet.format(f'B2:B{data_rows}', number_format)  # הנחה %
                worksheet.format(f'C2:C{data_rows}', number_format)  # תמחור שעה
                worksheet.format(f'G2:G{data_rows}', number_format)  # סהכ שעות
                worksheet.format(f'A2:A{data_rows}', summary_format)  # סיכום
                
                # Format columns with text
                text_format = {
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                worksheet.format(f'D2:F{data_rows}', text_format)  # מדריך, לפי מדריך, לקוח
            
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

class InstitutionalClientsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #d3d3d3;")
        main_layout = QVBoxLayout(self)
        header = QLabel("לקוחות מוסדיים", self)
        header.setFont(QFont("Arial", int(40 * 1.3), QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: blue; background: transparent;")
        main_layout.addWidget(header)

        # Add top controls layout
        top_controls = QHBoxLayout()

        # Add client button
        add_btn = QPushButton("הוספת לקוח", self)
        add_btn.setFixedWidth(120)
        add_btn.setFont(QFont("Arial", int(14 * 1.3)))
        add_btn.setStyleSheet("""
            QPushButton {
                color: black;
                background-color: #90EE90;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #98FB98;
            }
        """)
        add_btn.clicked.connect(self.add_new_client)
        top_controls.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        top_controls.addStretch()  # Push button to the left
        main_layout.addLayout(top_controls)

        # Table
        self.table = ResizableTable(self)
        header_font_size = int(17 * 1.3)
        header_style = f"QHeaderView::section {{ color: blue; font-weight: bold; font-family: Arial; font-size: {header_font_size}px; }}"
        self.table.horizontalHeader().setStyleSheet(header_style)
        self.table.verticalHeader().setStyleSheet(header_style)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        # Enable bidirectional sorting
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().sortIndicatorChanged.connect(self.handle_sort)
        self.table.cellClicked.connect(self.show_client_card)
        default_height = self.table.verticalHeader().defaultSectionSize()
        self.table.verticalHeader().setDefaultSectionSize(int(default_height * 1.3 * 1.3 * 1.3))
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

        main_layout.addLayout(bottom_buttons)

        self.setLayout(main_layout)
        self.headers = []
        self.clients = []
        self.sorted_row_indices = []
        self.load_clients()

    def handle_sort(self, column, order):
        self.table.sortItems(column, Qt.SortOrder(order))
        self.update_sorted_row_indices()

    def load_clients(self):
        try:
            gc = get_gspread_client()
            sheet_name = "לקוחות מוסדיים"
            spreadsheet_id = os.getenv("SPREADSHEET_ID")
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(sheet_name)
            # Fetch headers from A1-E1
            headers = worksheet.row_values(1)[:5]
            
            # Create ordered headers with fixed positions for גוף and הערות
            ordered_headers = []
            
            # Add גוף first (stays in first position)
            ordered_headers.append("גוף")
            
            # Add איש קשר, טלפון, מייל in order
            ordered_headers.extend(["איש קשר", "טלפון", "מייל"])
            
            # Add הערות last (stays in last position)
            ordered_headers.append("הערות")

            self.headers = ordered_headers
            self.table.setColumnCount(len(self.headers))
            self.table.setHorizontalHeaderLabels(self.headers)

            # Fetch all records
            self.clients = worksheet.get_all_records()
            
            # Get raw data to access column F for status
            raw_data = worksheet.get_all_values()
            
            # Update each record with status from column F (index 5)
            for i, record in enumerate(self.clients):
                if i + 1 < len(raw_data):  # +1 because records don't include header row
                    row_data = raw_data[i + 1]
                    if len(row_data) > 5:  # Make sure column F exists
                        status_from_col_f = row_data[5].strip()
                        # Set status based on column F
                        if status_from_col_f == "לא פעיל":
                            record['סטטוס'] = "לא פעיל"
                        else:
                            record['סטטוס'] = "פעיל"
            
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בטעינת לקוחות מוסדיים: {e}")

    def populate_table(self):
        self.table.setRowCount(len(self.clients))
        self.sorted_row_indices = list(range(len(self.clients)))
        font = QFont("Arial", int(17 * 1.3 * 0.9))
        
        # Sort clients - active first, then inactive ones
        active_clients = []
        inactive_clients = []
        for client in self.clients:
            if str(client.get('סטטוס', '')).strip() == "לא פעיל":
                inactive_clients.append(client)
            else:
                active_clients.append(client)
                
        row = 0
        for client in active_clients + inactive_clients:
            is_inactive = str(client.get('סטטוס', '')).strip() == "לא פעיל"
            color = QColor("gray") if is_inactive else QColor("black")

            for col, header in enumerate(self.headers):
                value = str(client.get(header, ''))
                if header == "מייל":
                    item = EmailTableItem(value)
                    item.setFont(font)
                    if is_inactive:
                        item.setBackground(QColor("#e0e0e0"))
                elif header == "טלפון":
                    item = PhoneTableItem(value)
                    item.setFont(font)
                    if is_inactive:
                        item.setBackground(QColor("#e0e0e0"))
                else:
                    item = QTableWidgetItem(value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFont(font)
                    item.setForeground(color)
                    if is_inactive:
                        item.setBackground(QColor("#e0e0e0"))

                item.setData(Qt.ItemDataRole.UserRole, is_inactive)
                self.table.setItem(row, col, item)
            row += 1

        self.table.setSortingEnabled(False)  # Prevent mixing active/inactive
        self.update_sorted_row_indices()

    def update_sorted_row_indices(self):
        row_map = []
        for row in range(self.table.rowCount()):
            first_col_item = self.table.item(row, 0)
            if first_col_item is None:
                continue
            first_col_val = first_col_item.text()
            # Try to match by first column value (usually name)
            for idx, client in enumerate(self.clients):
                if str(client.get(self.headers[0], '')) == first_col_val:
                    row_map.append(idx)
                    break
            else:
                row_map.append(-1)
        self.sorted_row_indices = row_map

    def show_client_card(self, row, col):
        # Email/Phone click functionality
        if self.headers:
            header = self.headers[col]
            item = self.table.item(row, col)
            if header == "טלפון":
                phone = item.text().strip()
                phone = ''.join(filter(str.isdigit, phone))
                if phone:
                    QDesktopServices.openUrl(QUrl(f"https://wa.me/972{phone[1:]}"))
                return
            if header == "מייל":
                email = item.text()
                QDesktopServices.openUrl(QUrl(f"mailto:{email}"))
                return
        # Show dialog for editing/viewing client details
        if hasattr(self, 'sorted_row_indices') and row < len(self.sorted_row_indices):
            client_idx = self.sorted_row_indices[row]
            if client_idx != -1:
                client = self.clients[client_idx]
            else:
                client = self.clients[row]
        else:
            client = self.clients[row]
        dlg = PrivateClientCardDialog(client, self.headers, self)
        # Change this to use a lambda to pass both self and client to update method
        dlg.update_client_in_sheet = lambda updates: self.update_client_in_sheet(client, updates)
        if dlg.exec():
            self.populate_table()  # Refresh table if edited

    def update_client_in_sheet(self, client, updates):
        gc = get_gspread_client()
        sheet_name = "לקוחות מוסדיים"
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet(sheet_name)
        all_records = worksheet.get_all_records()
        # Find the row by matching the institution name (גוף)
        for idx, record in enumerate(all_records):
            if str(record.get('גוף', '')).strip() == str(client.get('גוף', '')).strip():
                headers = worksheet.row_values(1)
                # Update all changed fields
                for field, value in updates.items():
                    if field in headers:
                        col_idx = headers.index(field) + 1
                        worksheet.update_cell(idx + 2, col_idx, value)
                # Add timestamp for last update if needed
                if 'עדכון אחרון' in headers:
                    timestamp_col = headers.index('עדכון אחרון') + 1
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    worksheet.update_cell(idx + 2, timestamp_col, now)
                    
                # If status was changed to "לא פעיל", also write it to column F
                if 'סטטוס' in updates and updates['סטטוס'] == 'לא פעיל':
                    # Column F is the 6th column (index 5 + 1 for gspread's 1-based indexing)
                    worksheet.update_cell(idx + 2, 6, 'לא פעיל')
                    
                    # Format the entire row with grey font
                    row_num = idx + 2
                    num_cols = len(headers)
                    cell_range = f'A{row_num}:{chr(65 + num_cols - 1)}{row_num}'
                    worksheet.format(cell_range, {
                        "textFormat": {
                            "foregroundColor": {
                                "red": 0.5,
                                "green": 0.5,
                                "blue": 0.5
                            }
                        }
                    })
                    
                # If status was changed to "פעיל", clear column F
                elif 'סטטוס' in updates and updates['סטטוס'] == 'פעיל':
                    worksheet.update_cell(idx + 2, 6, '')
                    
                    # Reset the entire row to black font
                    row_num = idx + 2
                    num_cols = len(headers)
                    cell_range = f'A{row_num}:{chr(65 + num_cols - 1)}{row_num}'
                    worksheet.format(cell_range, {
                        "textFormat": {
                            "foregroundColor": {
                                "red": 0,
                                "green": 0,
                                "blue": 0
                            }
                        }
                    })
                break

    def add_new_client(self):
        """Create and show dialog for new client"""
        # Create empty client data
        new_client = {header: '' for header in self.headers}
        dlg = PrivateClientCardDialog(new_client, self.headers, self)
        if dlg.exec():
            self.clients.append(new_client)
            self.add_client_to_sheet(new_client)
            self.populate_table()

    def add_client_to_sheet(self, client):
        """Add new client to the first empty row in the worksheet"""
        try:
            gc = get_gspread_client()
            sheet_name = "לקוחות מוסדיים"
            spreadsheet_id = os.getenv("SPREADSHEET_ID")
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(sheet_name)

            # Get all current clients to find the first empty row
            all_records = worksheet.get_all_records()
            next_row = len(all_records) + 2  # +2 for header row and 1-based indexing

            # Get headers to ensure correct column order
            headers = worksheet.row_values(1)

            # Create row values in the correct order
            row_values = []
            for header in headers:
                row_values.append(client.get(header, ''))

            # Add the new row
            worksheet.insert_row(row_values, next_row)
            
            # If client status is "לא פעיל", also write to column F
            if client.get('סטטוס', '') == 'לא פעיל':
                worksheet.update_cell(next_row, 6, 'לא פעיל')  # Column F is 6
                
                # Format the entire row with grey font
                num_cols = len(headers)
                cell_range = f'A{next_row}:{chr(65 + num_cols - 1)}{next_row}'
                worksheet.format(cell_range, {
                    "textFormat": {
                        "foregroundColor": {
                            "red": 0.5,
                            "green": 0.5,
                            "blue": 0.5
                        }
                    }
                })
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בהוספת לקוח: {e}")

    def mousePressEvent(self, event):
        item = self.table.itemAt(self.table.viewport().mapFrom(self, event.pos()))
        if item and isinstance(item, EmailTableItem):
            QDesktopServices.openUrl(QUrl(f"mailto:{item.text()}"))
        elif item and isinstance(item, PhoneTableItem):
            phone = item.text().strip()
            phone = ''.join(filter(str.isdigit, phone))
            if phone:
                QDesktopServices.openUrl(QUrl(f"https://wa.me/972{phone[1:]}"))
        else:
            super().mousePressEvent(event)

    def go_back(self):
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            mw.setCentralWidget(Dashboard(mw))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.go_back()
        super().keyPressEvent(event)

class OverflowEventsDialog(QDialog):
    def __init__(self, events, parent=None):
        super().__init__(parent)
        self.events = events
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("אירועים נוספים")
        self.setFixedWidth(300)
        self.setStyleSheet("""
            QDialog {
                background: #d3d3d3;
                border-radius: 15px;
                padding: 16px;
            }
            QLabel {
                color: black;
                font-size: 16px;
                margin: 4px;
                padding: 4px;
                border-radius: 6px;
            }
            QLabel:hover {
                background-color: #ADD8E6;
            }
            QPushButton {
                color: black;
                font-size: 16px;
                min-width: 80px;
                background-color: #e0e0e0;
                border-radius: 8px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create event labels with proper styling
        for event in events:
            event_label = QLabel(f"{event['time']} {event['title']}")
            event_label.setWordWrap(True)
            event_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            event_label.setFont(QFont("Arial", 16))
            event_label.setStyleSheet("color: black;")
            event_label.mousePressEvent = lambda e, ev=event: self.show_event_card(ev)
            layout.addWidget(event_label)

        # OK button with proper styling
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(self.accept)
        btn_box.setCenterButtons(True)
        btn = btn_box.button(QDialogButtonBox.StandardButton.Ok)
        if btn:
            btn.setFont(QFont("Arial", 16))
            btn.setStyleSheet("""
                QPushButton {
                    color: black;
                    background-color: #e0e0e0;
                    border-radius: 8px;
                    padding: 8px 24px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
            """)
        layout.addWidget(btn_box)

        self.setLayout(layout)

    def show_event_card(self, event):
        self.close()
        dlg = EventDetailsDialog2(event['raw_event'], self)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.exec()

class CalendarEventLabel(QLabel):
    def __init__(self, text, event=None, parent=None):
        super().__init__(text, parent)
        self.event = event
        self.setFont(QFont("Arial", 16))
        self.setStyleSheet("""
            QLabel {
                color: black;
                border-radius: 4px;
                padding: 2px 6px 2px 6px;
                font-size: 16px;
                background-color: %s;
            }
        """ % ("white" if "🌷" in text else "#e0e0e0"))
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                background-color: #90EE90;
                color: black;
                border-radius: 4px;
                padding: 2px 6px 2px 6px;
                font-size: 16px;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                background-color: %s;
                color: black;
                border-radius: 4px;
                padding: 2px 6px 2px 6px;
                font-size: 16px;
            }
        """ % ("white" if "🌷" in self.text() else "#e0e0e0"))
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if self.event and event.button() == Qt.MouseButton.LeftButton and "🌷" not in self.text():
            dlg = EventDetailsDialog2(self.event, self)
            dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dlg.exec()

class EventDetailsDialog2(QDialog):  # Renamed smaller dialog
    def __init__(self, event, parent=None):
        super().__init__(parent)
        self.setWindowTitle("פרטי אירוע")
        self.setFixedWidth(300)  # Compact width
        self.setStyleSheet("""
            QDialog {
                background: #d3d3d3;
                border-radius: 15px;
                padding: 16px;
            }
            QLabel {
                color: black;
                font-family: Arial;
                font-size: 16px;
                margin: 4px;
                padding: 4px;
                border-radius: 6px;
            }
            QLabel:hover {
                background-color: #ADD8E6;
            }
            QPushButton, QDialogButtonBox QPushButton {
                color: black;
                font-size: 16px;
                font-family: Arial;
                font-weight: bold;
                min-width: 80px;
                background: #e0e0e0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title (centered and compact)
        title_text = event.get('summary', 'אירוע ללא כותרת')
        title = QLabel(title_text)
        title.setFont(QFont("Arial", 16))
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Organizer (centered and compact)
        organizer = event.get('organizer', {}).get('email', '')
        if '@' in organizer:
            username = organizer.split('@')[0]
            instructor_name = self.get_instructor_name(username)
            org_label = QLabel(instructor_name)
            org_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            org_label.setFont(QFont("Arial", 16))
            layout.addWidget(org_label)

        # Date and Time (centered without labels)
        start = event.get('start', {})
        end = event.get('end', {})
        try:
            start_dt = datetime.fromisoformat(start.get('dateTime', start.get('date')))
            start_dt = start_dt.astimezone(pytz.timezone('Asia/Jerusalem'))
            end_dt = datetime.fromisoformat(end.get('dateTime', end.get('date')))
            end_dt = end_dt.astimezone(pytz.timezone('Asia/Jerusalem'))

            date_label = QLabel(start_dt.strftime('%d/%m/%Y'))
            time_label = QLabel(f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}")

            for lbl in [date_label, time_label]:
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setFont(QFont("Arial", 16))

            layout.addWidget(date_label)
            layout.addWidget(time_label)
        except:
            pass

        # Location (centered without label)
        if event.get('location'):
            loc_label = QLabel(event['location'])
            loc_label.setWordWrap(True)
            loc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            loc_label.setFont(QFont("Arial", 16))
            layout.addWidget(loc_label)

        # OK button (centered)
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(self.accept)
        btn_box.setCenterButtons(True)
        # Set button font and color
        btn = btn_box.button(QDialogButtonBox.StandardButton.Ok)
        if btn:
            btn.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            btn.setStyleSheet("color: black; background: #e0e0e0; border-radius: 8px;")
        layout.addWidget(btn_box)

    def get_instructor_name(self, username):
        try:
            instructors = fetch_instructors_from_google()
            for instructor in instructors:
                email = instructor.get('מייל', '').strip()
                if '@' in email and email.split('@')[0] == username:
                    return instructor.get('שם', username)
        except:
            pass
        return username

class CalendarScreen(QWidget):
    def update_clock(self):
        """Update the digital clock display."""
        tel_aviv_tz = pytz.timezone('Asia/Jerusalem')
        now = datetime.now(tel_aviv_tz)
        self.clock_label.setText(now.strftime("%H:%M"))
        # Update every minute
        QTimer.singleShot(60000, self.update_clock)

    def get_calendar_service(self):
        try:
            credentials = Credentials.from_service_account_file(
                self.SERVICE_ACCOUNT_FILE,
                scopes=self.SCOPES
            )
            return build('calendar', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Calendar service error: {str(e)}")
            return None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #d3d3d3;")

        # Initialize variables with proper timezone
        self.current_date = datetime.now(pytz.timezone('Asia/Jerusalem'))
        self.hebrew_days = ["שבת", "שישי", "חמישי", "רביעי", "שלישי", "שני", "ראשון"]
        self.day_frames = {}

        # Set up Google Calendar service
        self.SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
        self.CALENDAR_ID = os.getenv('CALENDAR_ID')
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.calendar_service = self.get_calendar_service()

        # Main layout
        main_layout = QVBoxLayout(self)

        # Header
        header = QLabel("לוח שנה", self)
        header.setFont(QFont("Arial", int(40 * 1.3), QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: blue; background: transparent;")
        main_layout.addWidget(header)

        # Navigation controls
        nav_frame = QHBoxLayout()
        
        # Right side - Navigation arrows (swapped order)
        right_side = QHBoxLayout()
        self.prev_btn = QPushButton("▶", self)
        self.next_btn = QPushButton("◀", self)
        
        # Style the arrow buttons
        for btn in [self.prev_btn, self.next_btn]:
            btn.setFixedWidth(40)
            btn.setFixedHeight(30)
            btn.setStyleSheet("""
                QPushButton {
                    color: black;
                    background-color: #ADD8E6;
                    border: 1px solid #808080;
                    border-radius: 4px;
                    font-size: 16px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #87CEEB;
                }
            """)
        
        self.prev_btn.clicked.connect(self.prev_period)
        self.next_btn.clicked.connect(self.next_period)
        
        right_side.addWidget(self.prev_btn)
        right_side.addWidget(self.next_btn)
        nav_frame.addLayout(right_side)

        # Period label in center
        center = QHBoxLayout()
        self.period_label = QLabel("", self)
        self.period_label.setStyleSheet("color: black; font-weight: bold; font-size: 14px;")
        self.period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(self.period_label)
        nav_frame.addLayout(center)
        nav_frame.addStretch()  # Add stretch to push everything to the right
        
        main_layout.addLayout(nav_frame)

        # Calendar container
        self.calendar_container = QWidget(self)
        self.calendar_container.setStyleSheet("background-color: white;")
        main_layout.addWidget(self.calendar_container)

        # Back button
        self.back_btn = QPushButton("חזרה", self)
        self.back_btn.setFixedWidth(120)
        self.back_btn.setFont(QFont("Arial", int(14 * 1.3)))
        self.back_btn.setStyleSheet("color: black;")
        self.back_btn.clicked.connect(self.go_back)
        main_layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.setLayout(main_layout)

        # Create initial view
        self.create_monthly_view()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Enable key events

    def create_monthly_view(self):
        """Create monthly calendar view."""
        # Clear existing layout
        if self.calendar_container.layout() is not None:
            QWidget().setLayout(self.calendar_container.layout())
        
        # Get all events for the month in one call at the start
        first_day = self.current_date.replace(day=1)
        if (first_day.month == 12):
            next_month = first_day.replace(year=first_day.year + 1, month=1, day=1)
        else:
            next_month = first_day.replace(month=first_day.month + 1, day=1)
        
        # Fetch all events for the month
        all_events = self.fetch_events_for_period(
            first_day.date(),
            (next_month - timedelta(days=1)).date()
        )

        layout = QVBoxLayout(self.calendar_container)

        # Update month-year header with Hebrew month names
        hebrew_months = {
            1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל", 
            5: "מאי", 6: "יוני", 7: "יולי", 8: "אוגוסט",
            9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר"
        }
        month_name = hebrew_months[self.current_date.month]
        month_year = f"{month_name} {self.current_date.year}"
        header = QLabel(f"חודש: {month_year}", self)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: blue;")
        layout.addWidget(header)

        # Calendar grid
        grid = QGridLayout()
        grid.setSpacing(1)

        # Day headers (reversed order for RTL)
        for i, day in enumerate(reversed(self.hebrew_days)):
            label = QLabel(day)
            label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 5px;
                color: blue;
            """)
            grid.addWidget(label, 0, i)

        # Get the first day of month and total days
        first_day = self.current_date.replace(day=1)
        if first_day.month == 12:
            next_month = first_day.replace(year=first_day.year + 1, month=1, day=1)
        else:
            next_month = first_day.replace(month=first_day.month + 1, day=1)
        days_in_month = (next_month - first_day).days

        # Calculate grid position (in our RTL grid: 6=Sunday, 0=Saturday)
        weekday = first_day.weekday()
        start_pos = (weekday + 1) % 7  # Adjust for RTL

        row = 1
        col = start_pos

        # Calendar cells
        today = datetime.now().date()
        for day in range(1, days_in_month + 1):
            cell_date = first_day.replace(day=day).date()
            is_today = cell_date == today

            cell = QFrame()
            cell.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
            cell.setStyleSheet(f"""
                QFrame {{
                    background-color: {'#FFCCCB' if is_today else 'white'};
                    border: 1px solid #ccc;
                    min-height: 120px;
                }}
            """)

            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(5, 5, 5, 5)
            cell_layout.setSpacing(2)

            # Day number (top-left, black font)
            day_label = QLabel(str(day))
            day_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            day_label.setStyleSheet("color: black;")
            day_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            day_label.setContentsMargins(2, 2, 0, 0)

            events = self.get_events_for_day(cell_date, all_events)
            if len(events) > 3:
                overflow_label = CalendarEventLabel(f"{day} 🌷")
                overflow_events = events[3:]
                def show_overflow(e, evts=overflow_events, cell=cell):
                    dlg = OverflowEventsDialog(evts, self)
                    # Position dialog near the cell, ensure fully visible (fallback to move if helper missing)
                    global_pos = cell.mapToGlobal(cell.rect().bottomLeft())
                    try:
                        dlg.move(self.ensure_dialog_visible(dlg, global_pos))
                    except AttributeError:
                        dlg.move(global_pos)
                    dlg.show()
                overflow_label.mousePressEvent = show_overflow
                cell_layout.addWidget(overflow_label)
            else:
                cell_layout.addWidget(day_label)

            for i, event in enumerate(events[:3]):
                event_label = CalendarEventLabel(f"{event['time']} {event['title']}", event['raw_event'])
                cell_layout.addWidget(event_label)

            cell_layout.addStretch()
            grid.addWidget(cell, row, col)

            col += 1
            if col > 6:
                col = 0
                row += 1

        # Set column stretch
        for i in range(7):
            grid.setColumnStretch(i, 1)

        layout.addLayout(grid)

    def fetch_events_for_period(self, start_date, end_date):
        """Fetch all events for a given period in a single API call."""
        if not self.calendar_service or not self.CALENDAR_ID:
            return []
        try:
            tz = pytz.timezone('Asia/Jerusalem')
            start_dt = tz.localize(datetime.combine(start_date, datetime.min.time()))
            end_dt = tz.localize(datetime.combine(end_date, datetime.max.time()))
            start_str = start_dt.isoformat()
            end_str = end_dt.isoformat()

            events_result = self.calendar_service.events().list(
                calendarId=self.CALENDAR_ID,
                timeMin=start_str,
                timeMax=end_str,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            # Get valid client names
            valid_clients = fetch_all_clients()

            # Pre-process events, filtering by valid client names - changed to substring check
            processed_events = []
            for event in events_result.get('items', []):
                title = event.get('summary', '').strip()
                # Check if any valid client name is contained in the title
                matching_client = None
                for client in valid_clients:
                    if client in title:
                        matching_client = client
                        break
                        
                if not title or not matching_client:
                    continue
                
                start = event['start'].get('dateTime', event['start'].get('date'))
                try:
                    dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M')
                except Exception:
                    time_str = ""
                processed_events.append({
                    'time': time_str,
                    'title': matching_client,  # Use just the matched client name instead of full title
                    'raw_event': event,
                    'date': dt.date()
                })
            return processed_events
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def get_events_for_day(self, date, all_events):
        """Filter pre-fetched events for a specific day."""
        return [event for event in all_events if event['date'] == date]

    def prev_period(self):
        """Go to previous month with proper timezone handling."""
        tz = pytz.timezone('Asia/Jerusalem')
        if self.current_date.month == 1:
            self.current_date = tz.localize(
                datetime(self.current_date.year - 1, 12, 1)
            )
        else:
            self.current_date = tz.localize(
                datetime(self.current_date.year, self.current_date.month - 1, 1)
            )
        self.create_monthly_view()

    def next_period(self):
        """Go to next month with proper timezone handling."""
        tz = pytz.timezone('Asia/Jerusalem')
        if self.current_date.month == 12:
            self.current_date = tz.localize(
                datetime(self.current_date.year + 1, 1, 1)
            )
        else:
            self.current_date = tz.localize(
                datetime(self.current_date.year, self.current_date.month + 1, 1)
            )
        self.create_monthly_view()

    def ensure_dialog_visible(self, dlg, pos):
        """Ensure the dialog is fully visible on screen."""
        screen = QApplication.primaryScreen().availableGeometry()
        x = pos.x()  # Changed from invalid x, y = pos.x(), y = pos.y()
        y = pos.y()
        if x + dlg.width() > screen.right():
            x = screen.right() - dlg.width()
        if y + dlg.height() > screen.bottom():
            y = screen.bottom() - dlg.height()
        if x < screen.left():
            x = screen.left()
        if y < screen.top():
            y = screen.top()
        return QPoint(x, y)

    def go_back(self):
        """Return to dashboard."""
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            mw.setCentralWidget(Dashboard(mw))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.go_back()
        super().keyPressEvent(event)

class Dashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #d3d3d3;")
        main_layout = QVBoxLayout(self)
        header = QLabel("לוח בקרה", self)
        header.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: blue; background: transparent;")
        main_layout.addWidget(header)
        main_layout.addSpacing(40)
        grid = QGridLayout()
        grid.setHorizontalSpacing(30)
        grid.setVerticalSpacing(60)
        cards = [
            ("מדריכים"),
            ("לקוחות פרטיים"),
            ("לקוחות מוסדיים"),
            ("לוח שנה"),
            ("חיובים"),
            ("תשלומים"),
        ]
        positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
        for idx, (row, col) in enumerate(positions):
            card = DashboardCard(cards[idx])
            if cards[idx] == "מדריכים":
                card.mousePressEvent = self.open_instructors
            elif cards[idx] == "לקוחות פרטיים":
                card.mousePressEvent = self.open_private_clients
            elif cards[idx] == "לקוחות מוסדיים":
                card.mousePressEvent = self.open_institutional_clients
            elif cards[idx] == "לוח שנה":
                card.mousePressEvent = self.open_calendar
            elif cards[idx] == "חיובים":  # New handler for billing
                card.mousePressEvent = self.open_billing
            elif cards[idx] == "תשלומים":  # New handler for payments
                card.mousePressEvent = self.open_payments
            grid.addWidget(card, row, col)
        grid.setContentsMargins(40, 0, 40, 0)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        main_layout.addLayout(grid)
        main_layout.addStretch()
        self.setLayout(main_layout)
        self.instructor_screen = None
        self.instructors_cache = None  # Store instructors in memory

    def open_instructors(self, event):
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            if self.instructors_cache is None:
                # First time: fetch from Google
                try:
                    self.instructors_cache = fetch_instructors_from_google()
                except Exception as e:
                    QMessageBox.critical(self, "שגיאה", f"שגיאה בטעינת מדריכים: {e}")
                    self.instructors_cache = []
            # Always create a new InstructorScreen, but pass the cached list
            self.instructor_screen = InstructorScreen(mw, instructors=self.instructors_cache)
            mw.setCentralWidget(self.instructor_screen)

    def open_private_clients(self, event):
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            mw.setCentralWidget(PrivateClientsScreen(mw))

    def open_institutional_clients(self, event):
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            mw.setCentralWidget(InstitutionalClientsScreen(mw))

    def open_calendar(self, event):
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            mw.setCentralWidget(CalendarScreen(mw))

    def open_billing(self, event):
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            mw.setCentralWidget(BillingScreen(mw))

    def open_payments(self, event):
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            mw.setCentralWidget(PaymentScreen(mw))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ניהול הדרכות")
        self.setMinimumSize(QSize(1200, 800))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.dashboard = Dashboard(self)
        self.setCentralWidget(self.dashboard)
        # Global caches for instructors and clients
        self.instructors_cache = None
        self.clients_cache = None

        # Preload instructors and clients in parallel
        self.preload_data()

    def preload_data(self):
        """Preload instructors and clients in parallel at app startup."""
        def fetch_instructors():
            try:
                self.instructors_cache = fetch_instructors_from_google(force_refresh=True)
            except Exception as e:
                print(f"Error preloading instructors: {e}")
                self.instructors_cache = []
        def fetch_clients():
            try:
                self.clients_cache = fetch_all_clients(force_refresh=True)
            except Exception as e:
                print(f"Error preloading clients: {e}")
                self.clients_cache = set()
        # Run both in parallel threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(fetch_instructors), executor.submit(fetch_clients)]
            concurrent.futures.wait(futures)

class PaymentScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("background-color: #d3d3d3;")
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Header layout
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
        self.month_year_combo.setEditable(True)
        line_edit = self.month_year_combo.lineEdit()
        line_edit.setReadOnly(True)
        line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title (left side)
        header = QLabel("תשלומים", self)
        header.setFont(QFont("Arial", int(40 * 1.3), QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: blue; background: transparent;")

        # Populate with current month
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        hebrew_months = [
            "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
            "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
        ]
        current_text = f"{hebrew_months[current_month-1]} {current_year}"
        self.month_year_combo.addItem(current_text, (current_month, current_year))
        for year in [current_year-1, current_year, current_year+1]:
            for month_idx, month in enumerate(hebrew_months, 1):
                if not (month_idx == current_month and year == current_year):
                    self.month_year_combo.addItem(f"{month} {year}", (month_idx, year))
        self.month_year_combo.setCurrentIndex(0)
        self.month_year_combo.currentIndexChanged.connect(self.populate_payment_data)

        # Add to layout
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
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setColumnCount(6)  # Updated column count after removing "Percentage"
        self.table.setHorizontalHeaderLabels(["מדריך", "  סהכ שעות  ", "לפי לקוח", "    לקוח    ", "שכר שעה", "סיכום"])
        # Set variable width for לקוח, hours, and percentage columns
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setStyleSheet("""
            QTableView {
                selection-background-color: #ADD8E6;
            }
            QTableView::item:hover {
                background-color: #ADD8E6;
            }
        """)
        default_height = self.table.verticalHeader().defaultSectionSize()
        self.table.verticalHeader().setDefaultSectionSize(int(default_height * 1.3 * 1.3))
        # Add click handler for hourly rate column
        self.table.cellClicked.connect(self.handle_cell_click)
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

        # Initialize cell rates dictionary to store rates per instructor per month
        self.cell_rates = {}
        
        # Initialize instructors map
        self.instructors_map = self._create_instructors_map()
        
        # Load saved cell rates
        self.load_cell_rates()
        
        # Populate the table
        self.populate_payment_data()

        # Add connection to export button
        self.export_btn.clicked.connect(self.export_to_sheets)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def get_current_month_year_key(self):
        """Get a string key for the current month and year"""
        month, year = self.month_year_combo.currentData()
        return f"{month}-{year}"
    
    def load_cell_rates(self):
        """Load hourly rates for each cell from Google Sheets"""
        try:
            gc = get_gspread_client()
            spreadsheet_id = os.getenv("payment_SPREADSHEET_ID")
            if not spreadsheet_id:
                return
                
            sh = gc.open_by_key(spreadsheet_id)
            
            # Try to get the hourly rates worksheet
            try:
                worksheet = sh.worksheet("שכר שעה")
                rates_data = worksheet.get_all_records()
                
                # Convert to dictionary format
                for record in rates_data:
                    if 'מדריך' in record and 'חודש' in record and 'שנה' in record and 'שכר שעה' in record:
                        instructor_name = record['מדריך']
                        month = record['חודש']
                        year = record['שנה']
                        hourly_rate = record['שכר שעה']
                        
                        # Create a unique key for this cell: instructor-month-year
                        cell_key = f"{instructor_name}-{month}-{year}"
                        self.cell_rates[cell_key] = hourly_rate
            except:
                # Create worksheet if it doesn't exist
                worksheet = sh.add_worksheet("שכר שעה", rows=100, cols=4)
                worksheet.update('A1:D1', [['מדריך', 'חודש', 'שנה', 'שכר שעה']])
        except Exception as e:
            print(f"Error loading cell rates: {e}")
    
    def save_cell_rate(self, instructor_name, rate):
        """Save or update an individual cell's hourly rate in Google Sheets"""
        try:
            gc = get_gspread_client()
            spreadsheet_id = os.getenv("payment_SPREADSHEET_ID")
            if not spreadsheet_id:
                return
                
            sh = gc.open_by_key(spreadsheet_id)
            
            # Get current month and year
            month, year = self.month_year_combo.currentData()
            
            try:
                worksheet = sh.worksheet("שכר שעה")
            except:
                # Create worksheet if it doesn't exist
                worksheet = sh.add_worksheet("שכר שעה", rows=100, cols=4)
                worksheet.update('A1:D1', [['מדריך', 'חודש', 'שנה', 'שכר שעה']])
            
            # Create a unique key for this cell
            cell_key = f"{instructor_name}-{month}-{year}"
            
            # Store in memory
            self.cell_rates[cell_key] = rate
            
            # Check if this cell already exists in the worksheet
            found = False
            all_data = worksheet.get_all_records()
            for idx, record in enumerate(all_data):
                if (record.get('מדריך') == instructor_name and 
                    record.get('חודש') == month and 
                    record.get('שנה') == year):
                    # Update existing record
                    row = idx + 2  # +2 for header and 1-based indexing
                    worksheet.update_cell(row, 4, rate)
                    found = True
                    break
            
            if not found:
                # Add new record
                next_row = len(all_data) + 2  # +2 for header row and 1-based indexing
                worksheet.update(f'A{next_row}:D{next_row}', 
                                [[instructor_name, month, year, rate]])
        except Exception as e:
            print(f"Error saving cell rate: {e}")

    def _create_instructors_map(self):
        """Create a mapping of email usernames to full instructor names."""
        instructors = fetch_instructors_from_google()
        email_to_name = {}
        for instructor in instructors:
            email = instructor.get('מייל', '').strip()
            if '@' in email:
                username = email.split('@')[0]
                email_to_name[username] = instructor.get('שם', username)
        return email_to_name

    def fetch_events_for_month(self):
        """Fetch events for the selected month."""
        try:
            month, year = self.month_year_combo.currentData()
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date()
            else:
                end_date = datetime(year, month + 1, 1).date()

            SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "SERVICE_ACCOUNT_FILE.json")
            SCOPES = ['https://www.googleapis.com/auth/calendar']
            CALENDAR_ID = os.getenv("CALENDAR_ID")

            credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            service = build('calendar', 'v3', credentials=credentials)

            events_result = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=start_date.isoformat() + 'T00:00:00Z',
                timeMax=end_date.isoformat() + 'T00:00:00Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            # Filter events by valid client names - modified to handle substring matches
            valid_clients = fetch_all_clients()
            filtered_events = []
            for event in events_result.get('items', []):
                title = event.get('summary', '').strip()
                # Find matching client name anywhere in the title
                matching_client = None
                for client in valid_clients:
                    if client in title:
                        matching_client = client
                        event['matched_client'] = client  # Store matched client name
                        filtered_events.append(event)
                        break
            
            return filtered_events
            
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def populate_payment_data(self):
        """Populate the payment table with data."""
        events = self.fetch_events_for_month()
        self.table.setRowCount(0)  # Clear existing rows

        valid_instructors = set(self.instructors_map.keys())
        data = {}

        for event in events:
            organizer_email = event.get('organizer', {}).get('email', '')
            if '@' in organizer_email:
                organizer_username = organizer_email.split('@')[0]
                if organizer_username in valid_instructors:
                    instructor_name = self.instructors_map[organizer_username]
                    # Use the matched_client name instead of full title
                    customer_name = event.get('matched_client', '')
                    
                    if not customer_name:  # Skip if no matched client
                        continue

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

                        if instructor_name not in data:
                            data[instructor_name] = {
                                'customers': {},  # Changed to dict to store hours per customer
                                'hours': 0
                            }

                        # Track hours per customer
                        if customer_name not in data[instructor_name]['customers']:
                            data[instructor_name]['customers'][customer_name] = 0
                        data[instructor_name]['customers'][customer_name] += duration
                        data[instructor_name]['hours'] += duration
                    except Exception as e:
                        print(f"Error processing event {event.get('summary', '')}: {e}")

        # Get current month and year
        month, year = self.month_year_combo.currentData()

        # Populate table with swapped columns
        for row, (instructor, details) in enumerate(data.items()):
            self.table.insertRow(row)

            # Define fonts before use
            base_font = self.table.font()
            big_font = QFont(base_font)
            big_font.setPointSize(base_font.pointSize() + 2)
            bold_font = QFont(big_font)
            bold_font.setBold(True)

            # מדריך column - dark green 2 and bold
            instructor_item = QTableWidgetItem(instructor)
            instructor_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            instructor_item.setFont(big_font)
            instructor_item.setForeground(QColor(0, 100, 0))
            bold_font = QFont(big_font)
            bold_font.setBold(True)
            instructor_item.setFont(bold_font)
            self.table.setItem(row, 0, instructor_item)

            # סהכ שעות column - dark green 2 and bold
            hours_item = QTableWidgetItem(f"{details['hours']:.1f}")
            hours_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            hours_item.setFont(bold_font)  # Use the same bold_font
            hours_item.setForeground(QColor(0, 100, 0))
            self.table.setItem(row, 1, hours_item)

            # לפי לקוח column - magenta
            hours_text = "\n".join(f"{hours:.1f}" for hours in details['customers'].values())
            hpc_item = QTableWidgetItem(hours_text)
            hpc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            hpc_item.setFont(base_font)
            hpc_item.setForeground(QColor(255, 0, 255))  # Changed from setData
            self.table.setItem(row, 2, hpc_item)

            # לקוח column - magenta
            customer_names = "\n".join(details['customers'].keys())
            customers_item = QTableWidgetItem(customer_names)
            customers_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            customers_item.setFont(base_font)
            customers_item.setForeground(QColor(255, 0, 255))  # Changed from setData
            self.table.setItem(row, 3, customers_item)

            # Get cell-specific hourly rate for this instructor and month/year
            cell_key = f"{instructor}-{month}-{year}"
            hourly_rate = self.cell_rates.get(cell_key, 200)  # Default to 200 if not found
            
            # שכר שעה column - default
            rate_item = QTableWidgetItem(str(hourly_rate))
            rate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rate_item.setFont(base_font)
            rate_item.setForeground(QColor(0, 0, 0))
            self.table.setItem(row, 4, rate_item)

            # סיכום column - dark green 2, bold
            total_payment = details['hours'] * float(hourly_rate)
            total_item = QTableWidgetItem(f"{total_payment:.2f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            total_item.setFont(bold_font)
            total_item.setForeground(QColor(0, 100, 0))  # Changed from setData
            self.table.setItem(row, 5, total_item)

            # Adjust row height based on the number of customers
            num_customers = len(details['customers'])
            base_height = 50  # Minimum row height
            height_per_customer = 25  # Height per customer line
            row_height = max(base_height, num_customers * height_per_customer)
            self.table.setRowHeight(row, row_height)

        # Enable text wrapping for customer cells
        for row in range(self.table.rowCount()):
            customers_item = self.table.item(row, 3)  # Adjusted to column 3
            if customers_item:
                customers_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                # Set word wrap to ensure text is visible
                customers_item.setFlags(customers_item.flags() | Qt.ItemFlag.ItemIsSelectable)

        # Remove width adjustability from סהכ שעות
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def handle_cell_click(self, row, col):
        """Handle cell clicks for hourly rate column and instructor popup"""
        if col == 0:  # מדריך column
            instructor_item = self.table.item(row, col)
            if not instructor_item:
                return
            instructor_name = instructor_item.text()
            
            # Fetch events for this instructor
            all_events = self.fetch_events_for_month()
            instructor_events = [
                e for e in all_events
                if e.get('organizer', {}).get('email', '').split('@')[0] in self.instructors_map and
                   self.instructors_map[e.get('organizer', {}).get('email', '').split('@')[0]] == instructor_name
            ]
            
            # Show the popup dialog
            dlg = InstructorEventsDialog(instructor_name, instructor_events, self)
            dlg.exec()
            return

        # Handle hourly rate column clicks (existing code)
        if col == 4:  # שכר שעה column
            item = self.table.item(row, col)
            current_value = item.text() if item else "200"
            instructor_item = self.table.item(row, 0)
            instructor_name = instructor_item.text() if instructor_item else ""
            
            # Create input dialog with black text
            input_dialog = QInputDialog(self)
            input_dialog.setInputMode(QInputDialog.InputMode.TextInput)
            input_dialog.setWindowTitle("שכר שעה")
            input_dialog.setLabelText("הכנס שכר שעה:")
            input_dialog.setTextValue(current_value)
            
            # Set all dialog elements to black text
            input_dialog.setStyleSheet("""
                QInputDialog {
                    color: black;
                }
                QInputDialog QLabel {
                    color: black;
                }
                QLineEdit {
                    color: black;
                }
                QPushButton {
                    color: black;
                }
            """)
            
            # Center align the text input
            line_edit = input_dialog.findChild(QLineEdit)
            if line_edit:
                line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if input_dialog.exec():
                try:
                    rate = float(input_dialog.textValue())
                    item.setText(str(rate))
                    
                    # Save the rate for this specific cell (instructor + month/year)
                    if instructor_name:
                        self.save_cell_rate(instructor_name, rate)
                    
                    # Update total payment
                    hours = float(self.table.item(row, 1).text())
                    total = hours * rate
                    
                    # Update total with dark green 2 color and bold font
                    total_item = self.table.item(row, 5)
                    total_item.setText(f"{total:.2f}")
                    current_font = total_item.font()
                    bold_font = QFont(current_font)  # Create new font based on current one
                    bold_font.setBold(True)
                    total_item.setFont(bold_font)
                    total_item.setForeground(QColor(0, 100, 0))
                except ValueError:
                    QMessageBox.warning(self, "שגיאה", "אנא הכנס מספר תקין")

    def go_back(self):
        mw = self.window()
        if hasattr(mw, 'setCentralWidget'):
            mw.setCentralWidget(Dashboard(mw))

    def export_to_sheets(self):
        """Export current payment data to Google Sheets with optimized batch operations"""
        try:
            # Get the month name and year for worksheet name
            month, year = self.month_year_combo.currentData()
            hebrew_months = [
                "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
            ]
            worksheet_name = f"{hebrew_months[month-1]} {year}"
            
            # Connect to Google Sheets
            gc = get_gspread_client()
            spreadsheet_id = os.getenv("payment_SPREADSHEET_ID")
            if not spreadsheet_id:
                raise Exception("Missing payment_SPREADSHEET_ID in babisteps.env")
                
            sh = gc.open_by_key(spreadsheet_id)
            
            # Track if worksheet is new to determine if we need full update
            is_new_worksheet = False
            try:
                worksheet = sh.worksheet(worksheet_name)
                # Get existing data to compare later
                existing_data = worksheet.get_all_values()
                if len(existing_data) == 0:
                    existing_data = [[""] * 6]  # Initialize with empty header row
            except:
                worksheet = sh.add_worksheet(worksheet_name, rows=100, cols=6)
                is_new_worksheet = True
                existing_data = [[""] * 6]  # Initialize with empty header row
            
            # Headers
            headers = ["סיכום", "שכר שעה", "לקוח", "לפי לקוח", "סהכ שעות", "מדריך"]
            
            # Prepare table data
            table_data = []
            for row in range(self.table.rowCount()):
                row_data = []
                for col in reversed(range(self.table.columnCount())):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else '')
                table_data.append(row_data)
            
            # Combine headers and data for batch comparison
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
            # Always update header row
            if 0 in rows_to_update or is_new_worksheet:
                worksheet.update('A1:F1', [headers])
                
            # Update only changed data rows
            for row_idx in rows_to_update:
                if row_idx > 0:  # Skip header (already updated)
                    row_num = row_idx + 1  # 1-indexed for sheets
                    row_range = f'A{row_num}:F{row_num}'
                    worksheet.update(row_range, [all_data[row_idx]])
            
            # Apply formatting in batches by column
            data_rows = len(all_data)
            
            # Header row formatting
            header_format = {
                'textFormat': {'bold': True, 'foregroundColor': {'red': 0, 'green': 0, 'blue': 1}},
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE'
            }
            
            # Column-specific formatting
            if data_rows > 1:  # Only if we have data
                # Apply header format
                worksheet.format('A1:F1', header_format)
                
                # Define column formats
                # Columns: מדריך and סהכ שעות with dark green format and bold
                dark_green_format = {
                    'textFormat': {
                        'foregroundColor': {'red': 0, 'green': 0.4, 'blue': 0},
                        'bold': True
                    },
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Columns: לפי לקוח and לקוח with magenta format
                magenta_format = {
                    'textFormat': {'foregroundColor': {'red': 1, 'green': 0, 'blue': 1}},
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Column: שכר שעה with black format
                black_format = {
                    'textFormat': {'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}},
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Column: סיכום with dark green format and bold
                summary_format = {
                    'textFormat': {
                        'foregroundColor': {'red': 0, 'green': 0.4, 'blue': 0},
                        'bold': True
                    },
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                }
                
                # Apply center alignment to all data cells first
                data_range = f'A2:F{data_rows}'
                worksheet.format(data_range, {'horizontalAlignment': 'CENTER', 'verticalAlignment': 'MIDDLE'})
                
                # Apply column-specific formats
                worksheet.format(f'A2:A{data_rows}', summary_format)    # סיכום
                worksheet.format(f'B2:B{data_rows}', black_format)      # שכר שעה
                worksheet.format(f'C2:D{data_rows}', magenta_format)    # לקוח & לפי לקוח
                worksheet.format(f'E2:F{data_rows}', dark_green_format) # סהכ שעות & מדריך
            
            # Show confirmation
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("הנתונים הועברו בהצלחה לגיליון אקסל")
            msg.setWindowTitle("ייצוא הושלם")
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #f0f0f0;
                }
                QMessageBox QLabel {
                    color: black;
                }
                QMessageBox QPushButton {
                    color: black;
                    padding: 5px 20px;
                }
            """)
            msg.exec()
                
        except Exception as e:
            QMessageBox.critical(self, "שגיאה", f"שגיאה בייצוא נתונים: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.go_back()
        super().keyPressEvent(event)

class ClientEventsDialog(QDialog):
    def __init__(self, client_name, events, instructors_map, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"אירועים עבור {client_name}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # RTL for Hebrew
        self.setStyleSheet("""
            QDialog { background: #f0f0f0; border-radius: 16px; }
            QTableWidget { background: white; }
            QHeaderView::section { color: blue; font-weight: bold; }
        """)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # RTL for table
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["כותרת", "מדריך", "תאריך", "שעה", "מס׳ שעות"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Only כותרת is dynamically adjustable
        self.table.setRowCount(len(events))
        self.table.setSortingEnabled(True)  # Enable sorting by clicking headers

        # Fill table and set alignment/font
        for row, event in enumerate(events):
            title_item = QTableWidgetItem(event.get('summary', ''))
            org_email = event.get('organizer', {}).get('email', '')
            username = org_email.split('@')[0] if '@' in org_email else ''
            instructor = instructors_map.get(username, username)
            instructor_item = QTableWidgetItem(instructor)
            start = event.get('start', {})
            end = event.get('end', {})
            try:
                start_dt = datetime.fromisoformat(start.get('dateTime', start.get('date')).replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.get('dateTime', end.get('date')).replace('Z', '+00:00'))
                date_str = start_dt.strftime('%d/%m/%Y')
                time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
                duration_hours = (end_dt - start_dt).total_seconds() / 3600
            except Exception:
                date_str, time_str, duration_hours = '', '', 0
            date_item = QTableWidgetItem(date_str)
            time_item = QTableWidgetItem(time_str)
            duration_item = QTableWidgetItem(f"{duration_hours:.1f}")

            for item in [title_item, instructor_item, date_item, time_item, duration_item]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor("black"))
                font = item.font()
                font.setPointSize(font.pointSize() + 2)
                item.setFont(font)

            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, instructor_item)
            self.table.setItem(row, 2, date_item)
            self.table.setItem(row, 3, time_item)
            self.table.setItem(row, 4, duration_item)

        # Set fixed column widths for all columns except כותרת
        for col in range(1, self.table.columnCount()):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, 120)

        layout.addWidget(self.table)

        # Swap: OK button on the left, Export (HTML) button on the right
        btn_layout = QHBoxLayout()
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(self.accept)
        btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        if btn:
            btn.setFont(QFont("Arial", 12))
            btn.setStyleSheet("color: black;")
        btn_layout.addWidget(btns, alignment=Qt.AlignmentFlag.AlignLeft)

        btn_layout.addStretch()

        self.html_btn = QPushButton("HTML ייצוא")
        self.html_btn.setFont(QFont("Arial", 12))
        self.html_btn.setStyleSheet("color: black;")
        self.html_btn.clicked.connect(self.export_table_to_html)
        btn_layout.addWidget(self.html_btn, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.adjustSize()
        self.setMinimumWidth(self.table.horizontalHeader().length() + 50)
        self.setMinimumHeight(self.table.verticalHeader().length() + 100)

    def export_table_to_html(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "שמור HTML", "", "HTML Files (*.html)")
        if not path:
            return
        html = '''
        <html dir="rtl">
        <head>
        <meta charset="utf-8">
        <style>
            body { direction: rtl; }
            table { border-collapse:collapse; font-family:Arial; font-size:14pt; direction:rtl; width:100%; }
            th, td { border:1px solid #000; padding:4px; text-align:right; direction:rtl; }
            th { background:#e0e0e0; }
        </style>
        </head>
        <body>
        '''
        html += '<table>'
        # Table headers
        html += "<tr>" + "".join(f"<th>{self.table.horizontalHeaderItem(i).text()}</th>" for i in range(self.table.columnCount())) + "</tr>"
        # Table data
        for row in range(self.table.rowCount()):
            html += "<tr>"
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                cell_text = item.text() if item else ''
                html += f"<td>{cell_text}</td>"
            html += "</tr>"
        html += "</table></body></html>"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        QMessageBox.information(self, "נשמר", f"שמור כ-HTML:\n{path}")

class InstructorEventsDialog(QDialog):
    def __init__(self, instructor_name, events, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"אירועים עבור {instructor_name}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("""
            QDialog { background: #f0f0f0; border-radius: 16px; }
            QTableWidget { background: white; }
            QHeaderView::section { color: blue; font-weight: bold; }
        """)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(self)
        self.table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["מדריך", "לקוח", "תאריך", "שעה", "מס׳ שעות"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for col in range(5):
            if col != 1:
                self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(col, 120)
        self.table.setRowCount(len(events))
        self.table.setSortingEnabled(True)

        for row, event in enumerate(events):
            instructor_item = QTableWidgetItem(instructor_name)
            client_item = QTableWidgetItem(event.get('summary', ''))
            start = event.get('start', {})
            end = event.get('end', {})
            try:
                start_dt = datetime.fromisoformat(start.get('dateTime', start.get('date')).replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.get('dateTime', end.get('date')).replace('Z', '+00:00'))
                date_str = start_dt.strftime('%d/%m/%Y')
                time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
                duration_hours = (end_dt - start_dt).total_seconds() / 3600
            except Exception:
                date_str, time_str, duration_hours = '', '', 0
            date_item = QTableWidgetItem(date_str)
            time_item = QTableWidgetItem(time_str)
            duration_item = QTableWidgetItem(f"{duration_hours:.1f}")

            for item in [instructor_item, client_item, date_item, time_item, duration_item]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor("black"))
                font = item.font()
                font.setPointSize(font.pointSize() + 2)
                item.setFont(font)

            self.table.setItem(row, 0, instructor_item)
            self.table.setItem(row, 1, client_item)
            self.table.setItem(row, 2, date_item)
            self.table.setItem(row, 3, time_item)
            self.table.setItem(row, 4, duration_item)

        layout.addWidget(self.table)

        # Swap: OK button on the left, Export (HTML) button on the right
        btn_layout = QHBoxLayout()
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(self.accept)
        btn = btns.button(QDialogButtonBox.StandardButton.Ok)
        if btn:
            btn.setFont(QFont("Arial", 12))
            btn.setStyleSheet("color: black;")
        btn_layout.addWidget(btns, alignment=Qt.AlignmentFlag.AlignLeft)

        btn_layout.addStretch()

        self.html_btn = QPushButton("HTML ייצוא")
        self.html_btn.setFont(QFont("Arial", 12))
        self.html_btn.setStyleSheet("color: black;")
        self.html_btn.clicked.connect(self.export_table_to_html)
        btn_layout.addWidget(self.html_btn, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.adjustSize()
        self.setMinimumWidth(self.table.horizontalHeader().length() + 50)
        self.setMinimumHeight(self.table.verticalHeader().length() + 100)

    def export_table_to_html(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "שמור HTML", "", "HTML Files (*.html)")
        if not path:
            return
        html = '''
        <html dir="rtl">
        <head>
        <meta charset="utf-8">
        <style>
            body { direction: rtl; }
            table { border-collapse:collapse; font-family:Arial; font-size:14pt; direction:rtl; width:100%; }
            th, td { border:1px solid #000; padding:4px; text-align:right; direction:rtl; }
            th { background:#e0e0e0; }
        </style>
        </head>
        <body>
        '''
        html += '<table>'
        # Table headers
        html += "<tr>" + "".join(f"<th>{self.table.horizontalHeaderItem(i).text()}</th>" for i in range(self.table.columnCount())) + "</tr>"
        # Table data
        for row in range(self.table.rowCount()):
            html += "<tr>"
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                cell_text = item.text() if item else ''
                html += f"<td>{cell_text}</td>"
            html += "</tr>"
        html += "</table></body></html>"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        QMessageBox.information(self, "נשמר", f"שמור כ-HTML:\n{path}")

if __name__ == "__main__":
    # Initialize gspread client at app startup
    get_gspread_client()
    app = QApplication(sys.argv)
    # Set application palette for better RTL/Hebrew support
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#d3d3d3"))  # Changed to light grey
    app.setPalette(palette)
    window = MainWindow()
    window.showFullScreen()  # Open in full screen
    sys.exit(app.exec())

