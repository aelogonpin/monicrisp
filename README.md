# Python Uptime Monitor

This project is a simple uptime monitoring application built with Python. It allows users to monitor the HTTP status of specified URLs in real-time and provides a dashboard to view the results.

## Features

- Monitor multiple URLs for their HTTP status.
- Real-time updates on the status of monitored URLs.
- Store monitoring results in a database.
- User-friendly web interface for inputting URLs and viewing results.

## Project Structure

```
python-uptime-monitor
├── src
│   ├── app.py                # Entry point of the application
│   ├── monitor               # Contains monitoring logic
│   │   ├── __init__.py
│   │   ├── checker.py        # UptimeChecker class for checking URL status
│   │   └── models.py         # Data models for monitoring results
│   ├── storage               # Handles database interactions
│   │   ├── __init__.py
│   │   └── database.py       # Methods for saving and retrieving results
│   ├── api                  # API routes for accessing monitoring data
│   │   ├── __init__.py
│   │   └── routes.py         # Defines API endpoints
│   └── utils                # Utility functions
│       ├── __init__.py
│       └── helpers.py        # Helper functions for various tasks
├── templates                 # HTML templates for the application
│   ├── index.html           # Main template for inputting URLs
│   └── dashboard.html        # Template for displaying monitoring results
├── static                    # Static files (CSS and JS)
│   ├── css
│   │   └── main.css          # CSS styles for the application
│   └── js
│       └── app.js            # JavaScript for client-side functionality
├── requirements.txt          # Project dependencies
├── config.py                 # Configuration settings
└── README.md                 # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/python-uptime-monitor.git
   cd python-uptime-monitor
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure the application settings in `config.py` as needed.

## Usage

1. Run the application:
   ```
   python src/app.py
   ```
2. To select the right level debug we can select with this options:
   ```
   # Minimum logging (critical errors only)
   python src/app.py --log-level critical
   
   # Error logging (errors only)
   python src/app.py --log-level error
   
   # Warning logging (warnings and errors)
   python src/app.py --log-level warning
   
   # Normal logging (default, informational messages)
   python src/app.py --log-level info
   
   # Detailed logging (for debugging and development)
   python src/app.py --log-level debug
   
   # Using the abbreviated form
   python src/app.py -l debug
   ```

2. Open your web browser and navigate to `http://localhost:5000` to access the application.

3. Input the URLs you want to monitor and view their status in real-time on the dashboard.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.