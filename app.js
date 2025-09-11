// Initialize the Telegram Web App
const tg = window.Telegram.WebApp;
tg.expand(); // Expand the web app to full height

const timeSlots = ["09:00", "10:00", "11:00", "13:00", "14:00", "16:00"];
const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

const table = document.getElementById('schedule-table');
const saveButton = document.getElementById('save-button');

// Generate the table grid
timeSlots.forEach(time => {
    const row = table.insertRow();
    const timeCell = row.insertCell();
    timeCell.textContent = time;

    days.forEach(day => {
        const cell = row.insertCell();
        cell.classList.add('editable');
        cell.dataset.day = day;
        cell.dataset.time = time;
    });
});

// Add click listener to editable cells
table.addEventListener('click', (event) => {
    const cell = event.target;
    if (cell.classList.contains('editable')) {
        const currentCode = cell.textContent;
        const newCode = prompt(`Enter course code for ${cell.dataset.day} at ${cell.dataset.time}:`, currentCode);
        if (newCode !== null) { // Handle cancel button
            cell.textContent = newCode.trim().toUpperCase();
        }
    }
});

// Handle the save button click
saveButton.addEventListener('click', () => {
    const scheduleTemplate = {};
    const cells = document.querySelectorAll('.editable');
    
    cells.forEach(cell => {
        const day = cell.dataset.day;
        const time = cell.dataset.time;
        const code = cell.textContent;

        if (code) { // Only add if there is a course code
            if (!scheduleTemplate[day]) {
                scheduleTemplate[day] = [];
            }
            scheduleTemplate[day].push({ time: time, code: code });
        }
    });

    // Send the data back to the bot
    tg.sendData(JSON.stringify(scheduleTemplate));
    // The web app will close after sending data
});