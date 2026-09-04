import sqlite3
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "veriscan.db"


def get_connection():
    """Create and return a SQLite database connection."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    """Create the verification history table if it does not exist."""
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS verification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type TEXT,
                entered_name TEXT,
                entered_document_number TEXT,
                detected_document_number TEXT,
                document_status TEXT,
                name_similarity REAL,
                format_valid INTEGER,
                rule_risk_score REAL,
                rule_risk_level TEXT,
                ai_status TEXT,
                ai_suspicious INTEGER,
                ai_confidence REAL,
                ai_risk_score REAL,
                ai_reasons TEXT,
                final_risk_score REAL,
                final_risk_level TEXT,
                created_at TEXT
            )
        """)

        connection.commit()

    finally:
        connection.close()


def save_verification(data):
    """Save one verification result to the database."""
    connection = get_connection()

    try:
        connection.execute("""
            INSERT INTO verification_history (
                document_type,
                entered_name,
                entered_document_number,
                detected_document_number,
                document_status,
                name_similarity,
                format_valid,
                rule_risk_score,
                rule_risk_level,
                ai_status,
                ai_suspicious,
                ai_confidence,
                ai_risk_score,
                ai_reasons,
                final_risk_score,
                final_risk_level,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("document_type"),
            data.get("entered_name"),
            data.get("entered_document_number"),
            data.get("detected_document_number"),
            data.get("document_status"),
            data.get("name_similarity"),
            data.get("format_valid"),
            data.get("rule_risk_score"),
            data.get("rule_risk_level"),
            data.get("ai_status"),
            data.get("ai_suspicious"),
            data.get("ai_confidence"),
            data.get("ai_risk_score"),
            data.get("ai_reasons"),
            data.get("final_risk_score"),
            data.get("final_risk_level"),
            data.get("created_at", datetime.now().isoformat())
        ))

        connection.commit()

    finally:
        connection.close()


def get_history(limit=20):
    """Return recent verification history."""
    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT
                id,
                document_type,
                entered_document_number,
                detected_document_number,
                final_risk_score,
                final_risk_level,
                created_at
            FROM verification_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()