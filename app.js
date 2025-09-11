// Initialize the Telegram Web App
const tg = window.Telegram.WebApp;
tg.expand();

// IMPORTANT: Replace this with the URL of your deployed server.py from Part 1
const API_SERVER_URL = "https://your-flask-server-url.com"; 

const timeSlots = ["09:00", "10:00", "11:00", "13:00", "14:00", "16:00"];
const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

const table = document.getElementById('schedule-table');
const saveButton = document.getElementById('save-button');

// --- Functions ---

function populateTable(scheduleData) {
    if (!scheduleData) return;

    for (const day in scheduleData) {
        scheduleData[day].forEach(classEntry => {
            const time = classEntry.time;
            const code = classEntry.code;
            // Find the correct cell in the grid
            const cell = document.querySelector(`td[data-day='${day}'][data-time='${time}']`);
            if (cell) {
                cell.textContent = code;
            }
        });
    }
}

async function loadSchedule() {
    // Get user_id from the URL (which the bot will add)
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id');

    if (!userId) {
        console.error("User ID not found in URL");
        return;
    }

    try {
        const response = await fetch(`${API_SERVER_URL}/get_schedule?user_id=${userId}`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const scheduleData = await response.json();
        populateTable(scheduleData);
    } catch (error) {
        console.error('Failed to load schedule:', error);
        // Let the user know something went wrong, but they can still create a new schedule
        alert("Could not load your saved schedule. You can create a new one.");
    }
}


// --- Event Listeners and Initial Setup ---

// Generate the empty table grid
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
        if (newCode !== null) {
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
        if (code) {
            if (!scheduleTemplate[day]) {
                scheduleTemplate[day] = [];
            }
            scheduleTemplate[day].push({ time: time, code: code });
        }
    });
    tg.sendData(JSON.stringify(scheduleTemplate));
});

// Load the user's schedule when the page is ready
document.addEventListener('DOMContentLoaded', loadSchedule);