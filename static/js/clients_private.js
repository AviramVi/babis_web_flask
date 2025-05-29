// Global variable to store clients data
let clientsData = [];

document.addEventListener('DOMContentLoaded', function() {
    // Get clients data from hidden element
    try {
        const clientsDataElement = document.getElementById('clientsData');
        if (clientsDataElement && clientsDataElement.textContent) {
            const parsedData = JSON.parse(clientsDataElement.textContent);
            // Ensure clientsData is an array
            clientsData = Array.isArray(parsedData) ? parsedData : [];
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
            // Don't trigger if clicking on a link (phone/email)
            if (e.target.closest('a')) {
                return; // Allow default link behavior for phone/email
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
        form.addEventListener('submit', function(e) {
            handleFormSubmit(e);
        });
    }
});

function openClientModal(clientData, sheetRow) {
    const modal = document.getElementById('clientModal');
    const form = document.getElementById('clientForm');
    
    if (!modal || !form) return;
    
    // Reset form
    form.reset();
    
    // Set sheet row value if provided
    if (sheetRow) {
        document.getElementById('sheetRow').value = sheetRow;
    }
    
    // If client data is provided, populate the form
    if (clientData) {
        document.getElementById('clientName').value = clientData['שם'] || '';
        document.getElementById('clientPhone').value = clientData['טלפון'] || '';
        document.getElementById('clientEmail').value = clientData['מייל'] || '';
        document.getElementById('clientSpecialNeed').value = clientData['צורך מיוחד'] || '';
        document.getElementById('clientNotes').value = clientData['הערות'] || '';
        
        // Set active status
        const isActive = !(clientData['פעיל'] && clientData['פעיל'].trim() === 'לא פעיל');
        document.getElementById('clientActive').checked = isActive;
        
        document.querySelector('.modal-header').textContent = 'עריכת לקוח';
    } else {
        // For new client
        document.getElementById('clientActive').checked = true;
        document.querySelector('.modal-header').textContent = 'הוספת לקוח חדש';
    }
    
    // Show the modal
    modal.style.display = 'flex';
    
    // Focus on the first input field
    const firstInput = form.querySelector('input:not([type="hidden"]), textarea');
    if (firstInput) {
        setTimeout(() => firstInput.focus(), 100);
    }
}

function openClientModalFromRow(row) {
    // Extract data from the row
    const sheetRow = row.dataset.sheetRow;
    const clientData = {
        'שם': row.cells[1]?.textContent || '',
        'טלפון': row.cells[2]?.textContent || '',
        'מייל': row.cells[3]?.querySelector('a')?.textContent || '',
        'צורך מיוחד': row.cells[4]?.textContent || '',
        'הערות': row.cells[5]?.textContent || '',
        'sheet_row': sheetRow,
        'פעיל': row.style.textDecoration === 'line-through' ? 'לא פעיל' : ''
    };
    
    openClientModal(clientData, sheetRow);
}

function sortTable(colIdx) {
    const table = document.querySelector('.clients-table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const isAsc = sortDirection[colIdx] = !sortDirection[colIdx];
    
    rows.sort((a, b) => {
        // Check if either row is inactive (strikethrough)
        const isInactive = row => {
            return row.classList.contains('inactive-client');
        };
        
        const aInactive = isInactive(a);
        const bInactive = isInactive(b);
        
        // Sort inactive clients to the bottom
        if (aInactive && !bInactive) return 1;
        if (!aInactive && bInactive) return -1;
        
        // If both are same (active/inactive), sort normally
        let aText = a.cells[colIdx].textContent.trim();
        let bText = b.cells[colIdx].textContent.trim();
        
        // Try to compare as numbers if possible (for phone numbers)
        let aNum = parseFloat(aText.replace(/[^\d.\-]/g, ''));
        let bNum = parseFloat(bText.replace(/[^\d.\-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAsc ? aNum - bNum : bNum - aNum;
        }
        
        // Otherwise compare as strings with RTL support
        return isAsc ? aText.localeCompare(bText, 'he') : bText.localeCompare(aText, 'he');
    });
    
    // Re-append sorted rows with updated indices
    rows.forEach((row, i) => {
        row.querySelector('.index-column').textContent = i + 1;
        tbody.appendChild(row);
    });
}

// Function to open modal with client data
function openClientModal(clientData, sheetRow) {
    const modal = document.getElementById('clientModal');
    const form = document.getElementById('clientForm');
    
    if (!modal || !form) return;
    
    // Reset form
    form.reset();
    
    // Set sheet row value if provided
    if (sheetRow) {
        document.getElementById('sheetRow').value = sheetRow;
    }
    
    // If client data is provided, populate the form
    if (clientData) {
        document.getElementById('clientName').value = clientData['שם'] || '';
        document.getElementById('clientPhone').value = clientData['טלפון'] || '';
        document.getElementById('clientEmail').value = clientData['מייל'] || '';
        document.getElementById('clientSpecialNeed').value = clientData['צורך מיוחד'] || '';
        document.getElementById('clientNotes').value = clientData['הערות'] || '';
        
        // Set active status
        const isActive = !(clientData['פעיל'] && clientData['פעיל'].trim() === 'לא פעיל');
        document.getElementById('clientActive').checked = isActive;
        
        document.querySelector('.modal-header').textContent = 'עריכת לקוח';
    } else {
        // For new client
        document.getElementById('clientActive').checked = true;
        document.querySelector('.modal-header').textContent = 'הוספת לקוח חדש';
    }
    
    // Show the modal
    modal.style.display = 'flex';
    
    // Focus on the first input field
    const firstInput = form.querySelector('input:not([type="hidden"]), textarea');
    if (firstInput) {
        setTimeout(() => firstInput.focus(), 100);
    }
}

function closeModal() {
    document.getElementById('clientModal').style.display = 'none';
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

async function handleFormSubmit(e) {
    e.preventDefault();
    
    const form = document.getElementById('clientForm');
    const clientId = document.getElementById('sheetRow').value; // Using sheetRow as the ID
    const sheetRow = document.getElementById('sheetRow').value;
    const isAdd = !sheetRow || sheetRow === 'new';
    
    const updatedData = {
        שם: document.getElementById('clientName').value,
        טלפון: document.getElementById('clientPhone').value,
        מייל: document.getElementById('clientEmail').value,
        'צורך מיוחד': document.getElementById('clientSpecialNeed').value,
        הערות: document.getElementById('clientNotes').value,
        'פעיל': document.getElementById('clientActive').checked ? '' : 'לא פעיל'
    };
    
    try {
        if (isAdd) {
            const response = await fetch('/add_private_client', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: updatedData })
            });
            
            const result = await response.json();
            
            if (result.success) {
                const tbody = document.querySelector('.clients-table tbody');
                const newRow = document.createElement('tr');
                const newIndex = tbody.rows.length + 1;
                newRow.setAttribute('data-row-index', newIndex);
                newRow.setAttribute('data-client-id', clientsData.length);
                newRow.setAttribute('data-sheet-row', result.sheet_row || '');
                
                if (updatedData['פעיל'] === 'לא פעיל') {
                    newRow.style.textDecoration = 'line-through';
                    newRow.style.color = '#888';
                }
                
                newRow.innerHTML = `
                    <td class="index-column">${newIndex}</td>
                    <td class="clickable-cell">${updatedData.שם}</td>
                    <td><a href="tel:${updatedData.טלפון}" class="phone-link">${updatedData.טלפון}</a></td>
                    <td><a href="mailto:${updatedData.מייל}" class="email-link">${updatedData.מייל}</a></td>
                    <td class="clickable-cell">${updatedData['צורך מיוחד']}</td>
                    <td class="clickable-cell">${updatedData.הערות}</td>
                `;
                
                newRow.querySelectorAll('.clickable-cell').forEach(cell => {
                    cell.addEventListener('click', function() {
                        const row = this.parentElement;
                        const clientId = parseInt(row.dataset.clientId);
                        const rowIndex = parseInt(row.dataset.rowIndex);
                        openClientModal(clientId, rowIndex);
                    });
                });
                
                tbody.appendChild(newRow);
                clientsData.push({ ...updatedData, sheet_row: result.sheet_row });
                showNotification('הלקוח נוסף בהצלחה');
            } else {
                console.error('Error adding client:', result.error);
                alert('שגיאה בהוספת לקוח: ' + (result.error || 'אנא נסו שנית'));
            }
        } else {
            console.log('Sending update request with data:', {
                sheet_row: parseInt(sheetRow),
                data: updatedData
            });
            
            const response = await fetch('/update_private_client', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sheet_row: parseInt(sheetRow),
                    data: updatedData
                })
            });
            
            console.log('Received response status:', response.status);
            const result = await response.json().catch(e => {
                console.error('Failed to parse JSON response:', e);
                throw new Error('Invalid response from server');
            });
            
            console.log('Server response:', result);
            
            if (result && result.success) {
                const row = document.querySelector(`tr[data-sheet-row="${sheetRow}"]`);
                if (row) {
                    // Update row content
                    row.cells[1].textContent = updatedData.שם;
                    
                    // Update phone cell
                    const phoneCell = row.cells[2];
                    if (phoneCell) {
                        phoneCell.innerHTML = updatedData.טלפון ? 
                            `<a href="tel:${updatedData.טלפון}" class="phone-link">${updatedData.טלפון}</a>` : 
                            '';
                    }
                    
                    // Update email cell
                    const emailCell = row.cells[3];
                    if (emailCell) {
                        emailCell.innerHTML = updatedData.מייל ? 
                            `<a href="mailto:${updatedData.מייל}" class="email-link">${updatedData.מייל}</a>` : 
                            '';
                    }
                    
                    // Update other cells
                    if (row.cells[4]) row.cells[4].textContent = updatedData['צורך מיוחד'] || '';
                    if (row.cells[5]) row.cells[5].textContent = updatedData.הערות || '';

                    // Update row styling based on active status
                    if (updatedData['פעיל'] === 'לא פעיל') {
                        row.style.textDecoration = 'line-through';
                        row.style.color = '#888';
                        row.classList.add('inactive-client');
                    } else {
                        row.style.textDecoration = 'none';
                        row.style.color = '';
                        row.classList.remove('inactive-client');
                    }
                }
                
                // Update the data in memory
                const clientIndex = clientsData.findIndex(client => client && client.sheet_row == sheetRow);
                if (clientIndex !== -1) {
                    clientsData[clientIndex] = { ...clientsData[clientIndex], ...updatedData };
                }
                showNotification('הלקוח עודכן בהצלחה');
            } else {
                console.error('Error updating client:', result.error);
                alert('שגיאה בעדכון הלקוח: ' + (result.error || 'אנא נסו שנית'));
            }
        }
    } catch (error) {
        console.error('Error:', error);
        alert('שגיאה בעדכון הלקוח. אנא נסו שנית.');
    }
    closeModal();
}
