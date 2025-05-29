// This file contains JavaScript code for client-side functionality, such as handling user interactions and making AJAX requests to the Flask backend.

document.addEventListener('DOMContentLoaded', function() {
    // Function to fetch instructors and populate the table
    function fetchInstructors() {
        fetch('/api/instructors')
            .then(response => response.json())
            .then(data => {
                const tableBody = document.getElementById('instructors-table-body');
                tableBody.innerHTML = ''; // Clear existing rows
                data.forEach(instructor => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${instructor.name}</td>
                        <td>${instructor.phone}</td>
                        <td>${instructor.email}</td>
                        <td>${instructor.expertise}</td>
                        <td>${instructor.notes}</td>
                    `;
                    tableBody.appendChild(row);
                });
            })
            .catch(error => console.error('Error fetching instructors:', error));
    }

    // Function to handle adding a new instructor
    const addInstructorBtn = document.getElementById('add-instructor-btn');
    if (addInstructorBtn) {
        addInstructorBtn.addEventListener('click', function() {
            const newInstructor = {
                name: document.getElementById('new-instructor-name')?.value || '',
                phone: document.getElementById('new-instructor-phone')?.value || '',
                email: document.getElementById('new-instructor-email')?.value || '',
                expertise: document.getElementById('new-instructor-expertise')?.value || '',
                notes: document.getElementById('new-instructor-notes')?.value || '',
            };

            fetch('/api/instructors', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newInstructor),
            })
            .then(response => response.json())
            .then(data => {
                console.log('Instructor added:', data);
                fetchInstructors(); // Refresh the instructor list
            })
            .catch(error => console.error('Error adding instructor:', error));
        });
    }

    // Initial fetch of instructors - only if we're on a page with the instructors table
    const instructorsTable = document.getElementById('instructors-table-body');
    if (instructorsTable) {
        fetchInstructors();
    }
});