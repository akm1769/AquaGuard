"""SQLite database module for AquaGuard.

Provides centralized database access for farms, ponds, water-quality readings,
disease predictions, and alerts. Uses the built-in sqlite3 library.

All connections enforce PRAGMA foreign_keys=ON and use a consistent path
resolved from this module's location.

The frontend sends farm_id="demo-farm-001" as a string. To avoid breaking
this contract, farms.id is TEXT and stores the exact farm_id from the API.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# Resolve database path relative to project root (one directory above backend/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_PROJECT_ROOT, "alerts.db")


def get_db_path() -> str:
    """Return the absolute path to the SQLite database file."""
    return _DB_PATH


def _get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with foreign keys enabled.

    Returns:
        sqlite3.Connection with foreign_keys=ON.

    Note:
        Callers must close the connection (use context manager or try/finally).
    """
    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row  # Enable named-column access
    return conn


def init_db() -> None:
    """Initialize the database schema.

    Creates all tables if they do not exist. Does not modify existing tables.
    Safe to call multiple times. Raises on error.

    Schema:
        - farms (id TEXT PRIMARY KEY, name TEXT, location TEXT, created_at TEXT)
        - ponds (id INTEGER PRIMARY KEY, farm_id TEXT -> farms.id, ...)
        - water_quality_readings (...)
        - disease_predictions (...)
        - alerts (existing, preserved)
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()

        # Farms table: id is TEXT to match the frontend's farm_id string
        cur.execute("""
            CREATE TABLE IF NOT EXISTS farms (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Ponds table: many ponds per farm
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ponds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id TEXT NOT NULL,
                name TEXT NOT NULL,
                species TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE
            )
        """)

        # Water quality readings: one per POST /water-quality call
        cur.execute("""
            CREATE TABLE IF NOT EXISTS water_quality_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id TEXT NOT NULL,
                pond_id INTEGER,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                ph REAL,
                dissolved_oxygen REAL,
                ammonia REAL,
                temperature REAL,
                risk_level TEXT,
                risk_score INTEGER,
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
                FOREIGN KEY (pond_id) REFERENCES ponds(id) ON DELETE SET NULL
            )
        """)

        # Disease predictions: one per POST /disease call
        cur.execute("""
            CREATE TABLE IF NOT EXISTS disease_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id TEXT NOT NULL,
                pond_id INTEGER,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                predicted_disease TEXT,
                confidence REAL,
                model_version TEXT,
                FOREIGN KEY (farm_id) REFERENCES farms(id) ON DELETE CASCADE,
                FOREIGN KEY (pond_id) REFERENCES ponds(id) ON DELETE SET NULL
            )
        """)

        # Indexes for common lookups
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ponds_farm_id ON ponds(farm_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wq_farm_id ON water_quality_readings(farm_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wq_pond_id ON water_quality_readings(pond_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wq_timestamp ON water_quality_readings(timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dp_farm_id ON disease_predictions(farm_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dp_timestamp ON disease_predictions(timestamp)")

        # The alerts table is created by alerts/notifier.py and preserved as-is.
        # We do not recreate or modify it here.

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Database initialization failed: {e}") from e
    finally:
        conn.close()


def ensure_farm_exists(farm_id: str, name: Optional[str] = None, location: Optional[str] = None) -> None:
    """Ensure a farm row exists for the given farm_id.

    If the farm already exists, this is a no-op. If it does not exist,
    a new row is inserted with the provided name and location.

    Args:
        farm_id: The primary key (e.g., "demo-farm-001").
        name: Optional display name. Defaults to farm_id if not provided.
        location: Optional location string.

    Raises:
        sqlite3.Error on database failure.
    """
    if not farm_id:
        raise ValueError("farm_id must not be empty")

    conn = _get_connection()
    try:
        cur = conn.cursor()
        # Check if farm exists
        cur.execute("SELECT id FROM farms WHERE id = ?", (farm_id,))
        if cur.fetchone() is None:
            # Insert new farm
            farm_name = name if name else farm_id
            cur.execute(
                "INSERT INTO farms (id, name, location) VALUES (?, ?, ?)",
                (farm_id, farm_name, location)
            )
            conn.commit()
    finally:
        conn.close()


def insert_water_quality_reading(
    farm_id: str,
    ph: float,
    dissolved_oxygen: float,
    ammonia: float,
    temperature: float,
    risk_level: str,
    risk_score: int,
    pond_id: Optional[int] = None,
    timestamp: Optional[str] = None
) -> int:
    """Insert a water quality reading and return the new row ID.

    Args:
        farm_id: The farm ID (must already exist in farms table).
        ph, dissolved_oxygen, ammonia, temperature: Measured values.
        risk_level: Computed risk level string.
        risk_score: Computed risk score (0-8).
        pond_id: Optional pond ID (nullable).
        timestamp: Optional ISO timestamp string. Defaults to now.

    Returns:
        The inserted row's ID.

    Raises:
        sqlite3.IntegrityError if farm_id does not exist.
        sqlite3.Error on any database failure.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        ts = timestamp if timestamp else datetime.utcnow().isoformat() + "Z"
        cur.execute("""
            INSERT INTO water_quality_readings
                (farm_id, pond_id, timestamp, ph, dissolved_oxygen, ammonia, temperature, risk_level, risk_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (farm_id, pond_id, ts, ph, dissolved_oxygen, ammonia, temperature, risk_level, risk_score))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def insert_disease_prediction(
    farm_id: str,
    predicted_disease: str,
    confidence: float,
    pond_id: Optional[int] = None,
    model_version: Optional[str] = None,
    timestamp: Optional[str] = None
) -> int:
    """Insert a disease prediction and return the new row ID.

    Args:
        farm_id: The farm ID (must already exist in farms table).
        predicted_disease: The model's predicted label.
        confidence: Confidence score (0.0-1.0).
        pond_id: Optional pond ID (nullable).
        model_version: Optional model version string.
        timestamp: Optional ISO timestamp string. Defaults to now.

    Returns:
        The inserted row's ID.

    Raises:
        sqlite3.IntegrityError if farm_id does not exist.
        sqlite3.Error on any database failure.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        ts = timestamp if timestamp else datetime.utcnow().isoformat() + "Z"
        cur.execute("""
            INSERT INTO disease_predictions
                (farm_id, pond_id, timestamp, predicted_disease, confidence, model_version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (farm_id, pond_id, ts, predicted_disease, confidence, model_version))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def persist_water_quality_reading(
    farm_id: str,
    ph: float,
    dissolved_oxygen: float,
    ammonia: float,
    temperature: float,
    risk_level: str,
    risk_score: int,
    pond_id: Optional[int] = None,
    timestamp: Optional[str] = None
) -> int:
    """Atomically ensure the farm exists and insert a water-quality reading.

    Uses a single transaction so the farm row and the reading are created
    together. If either operation fails, both are rolled back.

    Args:
        farm_id: The farm ID (e.g., "demo-farm-001").
        ph, dissolved_oxygen, ammonia, temperature: Measured values.
        risk_level: Computed risk level string.
        risk_score: Computed risk score (0-8).
        pond_id: Optional pond ID (nullable).
        timestamp: Optional ISO timestamp string. Defaults to now.

    Returns:
        The inserted reading row ID.

    Raises:
        sqlite3.Error on any database failure (caller must handle).
    """
    if not farm_id:
        raise ValueError("farm_id must not be empty")

    conn = _get_connection()
    try:
        cur = conn.cursor()
        ts = timestamp if timestamp else datetime.utcnow().isoformat() + "Z"

        # Ensure farm exists (INSERT OR IGNORE for idempotency)
        cur.execute(
            "INSERT OR IGNORE INTO farms (id, name, location) VALUES (?, ?, ?)",
            (farm_id, farm_id, None)
        )

        # Insert the reading
        cur.execute("""
            INSERT INTO water_quality_readings
                (farm_id, pond_id, timestamp, ph, dissolved_oxygen, ammonia, temperature, risk_level, risk_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (farm_id, pond_id, ts, ph, dissolved_oxygen, ammonia, temperature, risk_level, risk_score))

        conn.commit()
        return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def persist_disease_prediction(
    farm_id: str,
    predicted_disease: str,
    confidence: float,
    pond_id: Optional[int] = None,
    model_version: Optional[str] = None,
    timestamp: Optional[str] = None
) -> int:
    """Atomically ensure the farm exists and insert a disease prediction.

    Uses a single transaction so the farm row and the prediction are created
    together. If either operation fails, both are rolled back.

    Args:
        farm_id: The farm ID (e.g., "demo-farm-001").
        predicted_disease: The model's predicted label.
        confidence: Confidence score (0.0-1.0).
        pond_id: Optional pond ID (nullable).
        model_version: Optional model version string.
        timestamp: Optional ISO timestamp string. Defaults to now.

    Returns:
        The inserted prediction row ID.

    Raises:
        sqlite3.Error on any database failure (caller must handle).
    """
    if not farm_id:
        raise ValueError("farm_id must not be empty")

    conn = _get_connection()
    try:
        cur = conn.cursor()
        ts = timestamp if timestamp else datetime.utcnow().isoformat() + "Z"

        # Ensure farm exists (INSERT OR IGNORE for idempotency)
        cur.execute(
            "INSERT OR IGNORE INTO farms (id, name, location) VALUES (?, ?, ?)",
            (farm_id, farm_id, None)
        )

        # Insert the prediction
        cur.execute("""
            INSERT INTO disease_predictions
                (farm_id, pond_id, timestamp, predicted_disease, confidence, model_version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (farm_id, pond_id, ts, predicted_disease, confidence, model_version))

        conn.commit()
        return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_alerts_for_farm(farm_id: str) -> List[Dict[str, Any]]:
    """Retrieve alerts for a farm using named-column access.

    Fixes the column-mapping bug by using an explicit SELECT list.

    Args:
        farm_id: The farm ID to filter by.

    Returns:
        List of dicts with keys: id, disease, severity, message.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, disease_type, severity, message
            FROM alerts
            WHERE farm_id = ?
            ORDER BY timestamp DESC
        """, (farm_id,))
        rows = cur.fetchall()
        return [
            {"id": row["id"], "disease": row["disease_type"], "severity": row["severity"], "message": row["message"]}
            for row in rows
        ]
    finally:
        conn.close()
