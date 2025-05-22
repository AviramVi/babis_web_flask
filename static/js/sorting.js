class SortableTable {
    constructor(table, options = {}) {
        this.table = table;
        this.options = {
            sortBy: 0,
            sortOrder: 'asc',
            activeClassName: 'active',
            headerClass: 'sortable',
            sortFunction: null,
            ...options
        };
        
        this.init();
    }
    
    init() {
        const headers = this.table.querySelectorAll(`thead th.${this.options.headerClass}`);
        
        headers.forEach((header, index) => {
            if (header.classList.contains(this.options.headerClass)) {
                header.addEventListener('click', () => this.sort(index));
                
                // Add sort indicator (single arrow icon)
                const icon = document.createElement('i');
                icon.className = 'fas fa-arrow-up sort-icon';
                header.appendChild(icon);
            }
        });
        
        // Initial sort
        this.sort(this.options.sortBy, this.options.sortOrder);
    }
    
    sort(columnIndex, order = null) {
        const tbody = this.table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const headers = this.table.querySelectorAll('th');
        
        // Toggle sort order if clicking the same column
        if (this.options.sortBy === columnIndex) {
            this.options.sortOrder = order || (this.options.sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            this.options.sortBy = columnIndex;
            this.options.sortOrder = order || 'asc';
        }
        
        // Update header classes and sort indicators
        headers.forEach((header, idx) => {
            if (header.classList.contains('sortable')) {
                // Hide all sort icons by default
                const icon = header.querySelector('.sort-icon');
                if (icon) {
                    icon.style.opacity = '0';
                }
                
                // Reset sort classes
                header.classList.remove('sort-asc', 'sort-desc');
                
                if (idx === columnIndex) {
                    // Add the appropriate sort class
                    const sortClass = this.options.sortOrder === 'asc' ? 'sort-asc' : 'sort-desc';
                    header.classList.add(sortClass);
                    
                    // Show and update the sort icon
                    if (icon) {
                        icon.style.opacity = '1';
                    }
                }
            }
        });
        
        // Separate active and inactive (strikethrough) rows
        const activeRows = [];
        const inactiveRows = [];
        
        rows.forEach(row => {
            if (row.style.textDecoration === 'line-through' || 
                row.querySelector('td')?.style.textDecoration === 'line-through') {
                inactiveRows.push(row);
            } else {
                activeRows.push(row);
            }
        });
        
        // Sort only active rows
        activeRows.sort((rowA, rowB) => {
            const cellA = rowA.cells[columnIndex];
            const cellB = rowB.cells[columnIndex];
            
            if (this.options.sortFunction) {
                return this.options.sortFunction(
                    cellA, 
                    cellB, 
                    columnIndex, 
                    this.options.sortOrder
                );
            }
            
            // Default sorting
            const a = cellA.textContent.trim();
            const b = cellB.textContent.trim();
            
            // Try to compare as numbers
            const aNum = parseFloat(a.replace(/[^\d.-]/g, ''));
            const bNum = parseFloat(b.replace(/[^\d.-]/g, ''));
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return this.options.sortOrder === 'asc' ? aNum - bNum : bNum - aNum;
            }
            
            // Fall back to string comparison
            return this.options.sortOrder === 'asc' 
                ? a.localeCompare(b, 'he') 
                : b.localeCompare(a, 'he');
        });
        
        // Combine active (sorted) and inactive rows
        const sortedRows = [...activeRows, ...inactiveRows];
        
        // Reattach all rows
        sortedRows.forEach(row => tbody.appendChild(row));
    }
}

// Make SortableTable available globally
window.SortableTable = SortableTable;
