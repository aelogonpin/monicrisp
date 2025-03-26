class MonitorResult:
    def __init__(self, url, status, timestamp):
        self.url = url
        self.status = status
        self.timestamp = timestamp

    def __repr__(self):
        return f"<MonitorResult(url={self.url}, status={self.status}, timestamp={self.timestamp})>"