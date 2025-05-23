document.addEventListener('DOMContentLoaded', function() {
    // Get clients data from hidden element
    let clientsData = [];
    try {
        const clientsDataElement = document.getElementById('clientsData');
        if (clientsDataElement) {
            clientsData = JSON.parse(clientsDataElement.textContent);
        }
    } catch (e) {
        console.error('Error parsing clients data:', e);
        clientsData = [];
    }

    // Add new client button
    document.querySelector('.add-client')?.addEventListener('click', function() {
        openClientModal(null, null);
    });

    // Make table rows clickable to open edit modal
    const tbody = document.querySelector('.clients-table tbody');
    if (tbody) {
        tbody.addEventListener('click', function(e) {
            // Don't trigger if clicking on a link (phone/email) or button
            if (e.target.closest('a') || e.target.closest('button')) {
                return;
            }
            
            // Find the closest row that was clicked
            const row = e.target.closest('tr.client-row');
            if (!row) return;
            
            const sheetRow = row.dataset.sheetRow;
            if (!sheetRow) return;
            
            // Find client data by sheet_row
            const clientData = Array.isArray(clientsData) ? 
                clientsData.find(client => client && client.sheet_row == sheetRow) : null;
                
            if (clientData) {
                openClientModal(clientData, sheetRow);
            } else {
                // If no client data found, still open modal with basic info from the row
                openClientModalFromRow(row);
            }
        });
    }

    // Modal close handlers
    const modal = document.getElementById('clientModal');
    if (modal) {
        // Close when clicking outside content
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Close with escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && modal.style.display === 'flex') {
                closeModal();
            }
        });
    }

    // Close modal with close button
    document.querySelector('.close-button')?.addEventListener('click', closeModal);

    // Cancel button in modal
    document.querySelector('.cancel-btn')?.addEventListener('click', closeModal);

    // Form submission
    const form = document.getElementById('clientForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
});

// Form submission handler
async function handleFormSubmit(e) {
    e.preventDefault();
    
    const sheetRow = document.getElementById('sheetRow')?.value;
    const isAdd = !sheetRow || sheetRow === 'new';
    
    // Prepare the data object with the correct field names
    const updatedData = {
        'ארגון': document.getElementById('clientOrg').value,
        'איש קשר': document.getElementById('clientContact').value,
        'טלפון': document.getElementById('clientPhone').value,
        'מייל': document.getElementById('clientEmail').value,
        'הערות': document.getElementById('clientNotes').value,
        'פעיל': document.getElementById('clientActive').checked ? '' : 'לא פעיל'  // Empty string means active, 'לא פעיל' means inactive
    };
    
    console.log('Form data prepared:', updatedData);
    
    try {
        const url = isAdd ? '/add_institutional_client' : '/update_institutional_client';
        
        // For add, send the data directly in the request body
        // For update, include sheet_row in the request body
        const requestData = isAdd ? updatedData : {
            ...updatedData,
            sheet_row: parseInt(sheetRow)
        };
        
        console.log('Sending data to', url, ':', requestData);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Response data:', result);
        
        if (result.success) {
            // Reload the page to show updated data
            window.location.reload();
        } else {
            console.error('Error from server:', result.error);
            alert('אירעה שגיאה בשמירת הנתונים: ' + (result.error || 'שגיאה לא ידועה'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('אירעה שגיאה בשמירת הנתונים: ' + error.message);
    } finally {
        closeModal();
    }
}

function openClientModal(clientData, sheetRow) {
    console.log('Opening client modal with data:', clientData);
    
    const modal = document.getElementById('clientModal');
    const form = document.getElementById('clientForm');
    
    if (!modal || !form) {
        console.error('Modal or form element not found');
        return;
    }
    
    // Set sheet row value if provided
    if (sheetRow) {
        const sheetRowInput = document.getElementById('sheetRow');
        if (sheetRowInput) {
            sheetRowInput.value = sheetRow;
        } else {
            console.warn('sheetRow input not found');
        }
    }
    
    // Reset form only if no client data is provided
    if (!clientData) {
        form.reset();
        // Ensure active checkbox is checked for new clients
        const activeCheckbox = document.getElementById('clientActive');
        if (activeCheckbox) {
            activeCheckbox.checked = true;
        }
        
        // Set modal header for new client
        const modalHeader = document.querySelector('.modal-header');
        if (modalHeader) {
            modalHeader.textContent = 'הוספת לקוח חדש';
        }
    } else {
        console.log('Populating form with client data:', clientData);
        
        // Helper function to safely set value
        const setValue = (id, value) => {
            const element = document.getElementById(id);
            if (element) {
                element.value = value || '';
            } else {
                console.warn(`Element with ID ${id} not found`);
            }
        };
        
        // Set form field values - check both 'גוף' and 'ארגון' for the organization field
        const orgValue = clientData['ארגון'] || clientData['גוף'] || '';
        setValue('clientOrg', orgValue);
        setValue('clientContact', clientData['איש קשר'] || '');
        setValue('clientPhone', clientData['טלפון'] || '');
        setValue('clientEmail', clientData['מייל'] || '');
        setValue('clientNotes', clientData['הערות'] || '');
        
        console.log('Setting organization field to:', orgValue);
        
        // Set active status
        const isActive = !(clientData['פעיל'] && clientData['פעיל'].trim() === 'לא פעיל');
        const activeCheckbox = document.getElementById('clientActive');
        if (activeCheckbox) {
            activeCheckbox.checked = isActive;
        }
        
        // Update modal header for editing
        const modalHeader = document.querySelector('.modal-header');
        if (modalHeader) {
            modalHeader.textContent = 'עריכת לקוח';
        }
    }
    
    // Show the modal
    try {
        modal.style.display = 'flex';
        
        // Focus on the first input field
        const firstInput = form.querySelector('input:not([type="hidden"]), textarea');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        } else {
            console.warn('No input fields found in the form');
        }
    } catch (error) {
        console.error('Error in openClientModal:', error);
        // Still show the modal even if there was an error
        modal.style.display = 'flex';
    }
}

function openClientModalFromRow(row) {
    console.log('Opening modal from row data');
    console.log('Row data:', row);
    
    // Extract data from the row
    const sheetRow = row.dataset.sheetRow;
    const cells = Array.from(row.cells);
    
    console.log('Cells:', cells);
    
    // Get headers to map cells to fields
    const headerElements = document.querySelectorAll('.clients-table thead th');
    console.log('Header elements:', headerElements);
    
    const headers = Array.from(headerElements)
        .map(th => th.textContent.trim())
        .filter(header => header !== '#');
    
    console.log('Headers:', headers);
    
    const clientData = {
        'sheet_row': sheetRow,
        'פעיל': 'כן'  // Default to active
    };
    
    console.log('Initial client data:', clientData);
    
    // Map cell data to fields based on headers
    headers.forEach((header, index) => {
        // +1 to skip index column (first column is #)
        const cellIndex = index + 1;
        if (cellIndex >= cells.length) return;
        
        const cell = cells[cellIndex];
        if (!cell) return;
        
        // Special handling for the active status
        if (header === 'פעיל') {
            // Check if the row has the 'inactive' class or the cell text is 'לא פעיל'
            const cellValue = cell.textContent.trim();
            const isInactive = row.classList.contains('inactive') || cellValue === 'לא פעיל';
            clientData[header] = isInactive ? 'לא פעיל' : '';
            return;
        }
        
        // For other fields, get the cell content
        let cellValue = '';
        
        // Special handling for email and phone which might be links
        if (header === 'מייל' || header === 'טלפון') {
            const link = cell.querySelector('a');
            cellValue = link ? link.textContent.trim() : cell.textContent.trim();
        } else {
            // For regular text fields
            cellValue = cell.textContent.trim();
        }
        
        console.log(`Mapping header '${header}' at index ${cellIndex} to value:`, cellValue);
        
        if (header && cellValue !== undefined) {
            // Map the header to the correct field name if needed
            const fieldName = header === 'גוף' ? 'ארגון' : header;
            clientData[fieldName] = cellValue;
        }
    });
    
    console.log('Final client data before opening modal:', clientData);
    openClientModal(clientData, sheetRow);
}

function closeModal() {
    console.log('Closing modal');
    const modal = document.getElementById('clientModal');
    if (modal) {
        modal.style.display = 'none';
    } else {
        console.warn('Modal element not found when trying to close');
    }
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    if (!notification) return;
    
    notification.textContent = message;
    notification.className = 'notification';
    notification.classList.add(type === 'error' ? 'error' : 'success');
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}
