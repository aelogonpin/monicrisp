const apiUrl = '/api/status'; // API endpoint to fetch the status of monitored URLs

async function fetchStatus() {
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        updateDashboard(data);
    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

function updateDashboard(data) {
    const dashboard = document.getElementById('dashboard');
    dashboard.innerHTML = ''; // Clear existing content

    data.forEach(result => {
        const statusElement = document.createElement('div');
        statusElement.className = 'status-item';
        statusElement.innerHTML = `
            <p>URL: ${result.url}</p>
            <p>Status: ${result.status}</p>
            <p>Timestamp: ${new Date(result.timestamp).toLocaleString()}</p>
        `;
        dashboard.appendChild(statusElement);
    });
}

// Fetch status every 5 seconds
setInterval(fetchStatus, 5000);

// Initial fetch
fetchStatus();