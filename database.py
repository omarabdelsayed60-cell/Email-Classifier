import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import Config
from logger import logger


class DatabaseManager:
    """SQLite Database Manager for storing and querying processed email records."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or Config.DATABASE_PATH)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a database connection with dictionary row formatting."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initializes the SQLite schema if the table does not exist."""
        query = """
        CREATE TABLE IF NOT EXISTS processed_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id TEXT,
            subject TEXT,
            body TEXT,
            category TEXT,
            urgency TEXT,
            sentiment TEXT,
            summary TEXT,
            suggested_reply TEXT,
            key_entities TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                conn.commit()
                logger.info(f"Database initialized successfully at: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def insert_record(self, record: Dict[str, Any]) -> int:
        """Inserts a single email classification record."""
        query = """
        INSERT INTO processed_emails (
            email_id, subject, body, category, urgency, sentiment, summary, suggested_reply, key_entities, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            record.get("email_id", ""),
            record.get("subject", ""),
            record.get("body", ""),
            record.get("category", "General Inquiry"),
            record.get("urgency", "Medium"),
            record.get("sentiment", "Neutral"),
            record.get("summary", ""),
            record.get("suggested_reply", ""),
            ", ".join(record.get("key_entities", [])) if isinstance(record.get("key_entities"), list) else str(record.get("key_entities", "")),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid or 0

    def batch_insert_records(self, records: List[Dict[str, Any]]) -> int:
        """Batch inserts multiple records in a single transaction to prevent database locks."""
        if not records:
            return 0

        query = """
        INSERT INTO processed_emails (
            email_id, subject, body, category, urgency, sentiment, summary, suggested_reply, key_entities, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        rows = [
            (
                r.get("email_id", ""),
                r.get("subject", ""),
                r.get("body", ""),
                r.get("category", "General Inquiry"),
                r.get("urgency", "Medium"),
                r.get("sentiment", "Neutral"),
                r.get("summary", ""),
                r.get("suggested_reply", ""),
                ", ".join(r.get("key_entities", [])) if isinstance(r.get("key_entities"), list) else str(r.get("key_entities", "")),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            for r in records
        ]

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, rows)
                conn.commit()
                inserted_count = cursor.rowcount
                logger.info(f"Successfully batch inserted {inserted_count} records into SQLite.")
                return inserted_count
        except Exception as e:
            logger.error(f"Error batch inserting records: {e}")
            raise

    def get_all_records(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Retrieves recent processed email records from SQLite."""
        query = "SELECT * FROM processed_emails ORDER BY id DESC LIMIT ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Returns aggregation statistics for dashboard visualization."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Category distribution
            cursor.execute("SELECT category, COUNT(*) as count FROM processed_emails GROUP BY category")
            categories = {row["category"]: row["count"] for row in cursor.fetchall()}

            # Urgency distribution
            cursor.execute("SELECT urgency, COUNT(*) as count FROM processed_emails GROUP BY urgency")
            urgencies = {row["urgency"]: row["count"] for row in cursor.fetchall()}

            # Sentiment distribution
            cursor.execute("SELECT sentiment, COUNT(*) as count FROM processed_emails GROUP BY sentiment")
            sentiments = {row["sentiment"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as total FROM processed_emails")
            total = cursor.fetchone()["total"]

            return {
                "total_processed": total,
                "categories": categories,
                "urgencies": urgencies,
                "sentiments": sentiments,
            }


db_manager = DatabaseManager()
