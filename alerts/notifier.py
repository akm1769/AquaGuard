"""Alert notification system for aquaculture farms."""
import smtplib
import sqlite3
import json
from datetime import datetime
from typing import Optional

class AlertNotifier:
    """Handles sending alerts to farmers via SMS/Email."""

    def __init__(self, smtp_config: dict = None, db_path: str = "alerts.db"):
        self.smtp_config = smtp_config or {}
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for storing alerts."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id TEXT,
                timestamp TEXT,
                disease_type TEXT,
                severity TEXT,
                message TEXT,
                sent BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()
        conn.close()

    def send_alert(self, farm_id: str, disease: str, severity: str, message: str) -> int:
        """Send an alert to a farmer and return the inserted row ID.

        Args:
            farm_id: Farm identifier
            disease: Disease type
            severity: Severity level
            message: Alert message

        Returns:
            The inserted alert row ID.
        """
        # Store in DB first
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO alerts (farm_id, disease_type, severity, message, sent) VALUES (?, ?, ?, ?, ?)",
            (farm_id, disease, severity, message, False)
        )
        conn.commit()
        alert_id = cursor.lastrowid
        conn.close()

        # Simulate sending email/SMS (in production, integrate Twilio/SNS)
        print(f"[ALERT] Farm {farm_id}: {severity} - {disease}")
        print(f"       Message: {message}")
        print(f"       Alert ID: {alert_id}")
        return alert_id

    def get_pending_alerts(self, farm_id: str) -> list:
        """Get pending alerts for a farm.

        Uses named-column access via sqlite3.Row for correct mapping.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, farm_id, timestamp, disease_type, severity, message, sent FROM alerts WHERE farm_id=? ORDER BY timestamp DESC",
            (farm_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        # Return tuples for compatibility with existing callers
        return [
            (r["id"], r["farm_id"], r["timestamp"], r["disease_type"], r["severity"], r["message"], r["sent"])
            for r in rows
        ]

# Example usage configuration
SMTP_CONFIG = {
    "host": "smtp.example.com",
    "port": 587,
    "username": "alerts@example.com",
    "password": "secret",
    "from": "aqua-guard-alerts@example.com",
    "to": "farmer@example.com"
}

# Initialize notifier
notifier = AlertNotifier(SMTP_CONFIG)
