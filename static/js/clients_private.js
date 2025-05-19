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
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Add active status
    data['פעיל'] = data['active'] ? 'פעיל' : 'לא פעיל';
    delete data.active; // Remove the temporary field
    
    // Add row index for updates
    if (!isAdd) {
        data.row_index = document.getElementById('rowIndex').value;
    }
    
    try {
        const response = await fetch(isAdd ? '/add_private_client' : '/update_private_client', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('הלקוח נשמר בהצלחה');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showNotification('אירעה שגיאה בשמירת הלקוח', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('אירעה שגיאה', 'error');
    }
}
