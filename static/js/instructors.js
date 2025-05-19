// Table sorting for instructors.html

document.addEventListener('DOMContentLoaded', function() {
    const table = document.querySelector('.instructors-table');
    if (!table) return;
    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');
    let sortDirection = {};

    thead.querySelectorAll('th').forEach((th, colIdx) => {
        if (colIdx === 0) return; // skip index column
        th.style.cursor = 'pointer';
        th.addEventListener('click', function() {
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const isAsc = sortDirection[colIdx] = !sortDirection[colIdx];
            rows.sort((a, b) => {
                // Check if either row is inactive (strikethrough)
                const isInactive = row => {
                    // Style may be set inline or inherited, so check both
                    return row.style.textDecoration === 'line-through' || row.style.color === 'rgb(136, 136, 136)' || row.style.color === '#888' || row.style.color === 'gray' || row.style.color === 'grey';
                };
                const aInactive = isInactive(a);
                const bInactive = isInactive(b);
                if (aInactive && !bInactive) return 1;
                if (!aInactive && bInactive) return -1;
                // If both are same (active/inactive), sort normally
                let aText = a.cells[colIdx].innerText.trim();
                let bText = b.cells[colIdx].innerText.trim();
                // Try to compare as numbers if possible
                let aNum = parseFloat(aText.replace(/[^\d.\-]/g, ''));
                let bNum = parseFloat(bText.replace(/[^\d.\-]/g, ''));
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return isAsc ? aNum - bNum : bNum - aNum;
                }
                // Otherwise compare as strings
                return isAsc ? aText.localeCompare(bText, 'he') : bText.localeCompare(aText, 'he');
            });
            // Re-append sorted rows
            rows.forEach((row, i) => {
                row.querySelector('.index-column').textContent = i + 1;
                tbody.appendChild(row);
            });
        });
    });
});
