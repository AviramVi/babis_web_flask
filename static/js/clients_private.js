// Table sorting for clients_private.html

document.addEventListener('DOMContentLoaded', function() {
    const table = document.querySelector('.clients-table');
    if (!table) return;
    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');
    let sortDirection = {};

    // Initialize sort functionality for each header
    thead.querySelectorAll('th').forEach((th, colIdx) => {
        if (colIdx === 0) return; // Skip index column
        th.style.cursor = 'pointer';
        th.addEventListener('click', function() {
            sortTable(colIdx);
        });
    });

    // Make table rows clickable to open edit modal
    tbody.querySelectorAll('tr').forEach(row => {
        row.addEventListener('click', function(e) {
            // Don't trigger if clicking on a link (phone/email)
            if (e.target.tagName === 'A') return;
            
            const clientId = this.dataset.clientId;
            const rowIndex = this.dataset.rowIndex;
            openClientModal(clientId, rowIndex);
        });
    });

    // Add new client button
    document.querySelector('.add-client')?.addEventListener('click', function() {
        document.getElementById('clientForm').reset();
        document.getElementById('clientIndex').value = '';
        document.getElementById('rowIndex').value = '';
        document.getElementById('sheetRow').value = '';
        document.getElementById('clientActive').checked = true;
        document.querySelector('.modal-header').textContent = 'הוספת לקוח חדש';
        document.getElementById('clientModal').style.display = 'flex';
    });

    // Close modal when clicking outside content
    const modal = document.getElementById('clientModal');
    modal?.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Close modal with close button
    document.querySelector('.close-button')?.addEventListener('click', closeModal);

    // Cancel button in modal
    document.querySelector('.cancel-btn')?.addEventListener('click', closeModal);

    // Form submission
    const form = document.getElementById('clientForm');
    form?.addEventListener('submit', handleFormSubmit);

    const clientsData = JSON.parse('{{ clients|tojson|safe }}');
    
    // Add event listeners to clickable cells
    document.querySelectorAll('.clickable-cell').forEach(cell => {
        cell.addEventListener('click', function() {
            const row = this.parentElement;
            const clientId = parseInt(row.dataset.clientId);
            const rowIndex = parseInt(row.dataset.rowIndex);
            openClientModal(clientId, rowIndex);
        });
    });

    function openClientModal(clientId, rowIndex) {
        const client = clientsData[clientId];
        
        // Set form values
        document.getElementById('clientIndex').value = clientId;
        document.getElementById('rowIndex').value = rowIndex;
        document.getElementById('clientName').value = client['שם'] || '';
        document.getElementById('clientPhone').value = client['טלפון'] || '';
        document.getElementById('clientEmail').value = client['מייל'] || '';
        document.getElementById('clientSpecialties').value = client['התמחויות'] || '';
        document.getElementById('clientNotes').value = client['הערות'] || '';
        
        modal.style.display = 'flex';
    }
});

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

function openClientModal(clientId, rowIndex) {
    const row = document.querySelector(`tr[data-client-id="${clientId}"]`);
    if (!row) return;
    
    const form = document.getElementById('clientForm');
    form.reset();
    
    // Populate form fields from row data
    document.getElementById('clientIndex').value = clientId;
    document.getElementById('rowIndex').value = rowIndex;
    document.getElementById('sheetRow').value = row.dataset.sheetRow;
    document.getElementById('clientName').value = row.cells[1].textContent.trim();
    document.getElementById('clientPhone').value = row.cells[2].textContent.trim();
    document.getElementById('clientEmail').value = row.cells[3].querySelector('a')?.textContent.trim() || '';
    document.getElementById('clientSpecialNeed').value = row.cells[4].textContent.trim();
    document.getElementById('clientNotes').value = row.cells[5].textContent.trim();
    
    // Set active status based on row class
    document.getElementById('clientActive').checked = !row.classList.contains('inactive-client');
    
    document.querySelector('.modal-header').textContent = 'עריכת פרטי לקוח';
    document.getElementById('clientModal').style.display = 'flex';
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
    
    const form = e.target;
    const clientId = document.getElementById('clientIndex').value;
    const sheetRow = document.getElementById('sheetRow').value;
    const isAdd = !sheetRow;
    
    const updatedData = {
        שם: document.getElementById('clientName').value,
        טלפון: document.getElementById('clientPhone').value,
        מייל: document.getElementById('clientEmail').value,
        התמחויות: document.getElementById('clientSpecialNeed').value,
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
                    <td class="clickable-cell">${updatedData.התמחויות}</td>
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
                alert('שגיאה בהוספת לקוח. אנא נסו שנית.');
            }
        } else {
            const response = await fetch('/update_private_client', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sheet_row: parseInt(sheetRow),
                    data: updatedData
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                const row = document.querySelector(`tr[data-client-id="${clientId}"]`);
                if (row) {
                    // Update row content
                    row.cells[1].textContent = updatedData.שם;
                    row.cells[2].querySelector('a').textContent = updatedData.טלפון;
                    row.cells[2].querySelector('a').href = `tel:${updatedData.טלפון}`;
                    row.cells[3].querySelector('a').textContent = updatedData.מייל;
                    row.cells[3].querySelector('a').href = `mailto:${updatedData.מייל}`;
                    row.cells[4].textContent = updatedData.התמחויות;
                    row.cells[5].textContent = updatedData.הערות;

                    // Update row styling based on active status
                    if (updatedData['פעיל'] === 'לא פעיל') {
                        row.style.textDecoration = 'line-through';
                        row.style.color = '#888';
                    } else {
                        row.style.textDecoration = 'none';
                        row.style.color = '';
                    }
                }
                
                // Update the data in memory
                clientsData[clientId] = updatedData;
                showNotification('הלקוח עודכן בהצלחה');
            } else {
                alert('שגיאה בעדכון הלקוח. אנא נסו שנית.');
            }
        }
    } catch (error) {
        console.error('Error:', error);
        alert('שגיאה בעדכון הלקוח. אנא נסו שנית.');
    }
    closeModal();
}
