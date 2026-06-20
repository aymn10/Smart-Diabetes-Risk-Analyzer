import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "diabetes.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                gender TEXT DEFAULT '',
                date_of_birth TEXT,
                height_cm REAL,
                weight_kg REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                patient_name TEXT NOT NULL DEFAULT 'Anonymous',
                age REAL NOT NULL,
                pregnancies INTEGER DEFAULT 0,
                glucose REAL NOT NULL,
                blood_pressure REAL NOT NULL,
                skin_thickness REAL,
                insulin REAL,
                bmi REAL NOT NULL,
                diabetes_pedigree REAL DEFAULT 0.0,
                risk_score REAL NOT NULL,
                risk_category TEXT NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )"""
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(assessments)").fetchall()
        }
        if "user_id" not in columns:
            conn.execute("ALTER TABLE assessments ADD COLUMN user_id INTEGER")


# --- Users ---

def create_user_record(email: str, password_hash: str, full_name: str = "") -> int:
    now = _now()
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO users (email, password_hash, full_name, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (email, password_hash, full_name, now, now),
        )
        return cursor.lastrowid


def get_user_by_email(email: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def update_user_profile(user_id: int, data: dict):
    now = _now()
    with get_db() as conn:
        conn.execute(
            """UPDATE users SET
                full_name = ?, gender = ?, date_of_birth = ?,
                height_cm = ?, weight_kg = ?, updated_at = ?
               WHERE id = ?""",
            (
                data.get("full_name", ""),
                data.get("gender", ""),
                data.get("date_of_birth") or None,
                data.get("height_cm"),
                data.get("weight_kg"),
                now,
                user_id,
            ),
        )


# --- Assessments ---

def save_assessment(data: dict, report: dict, user_id: int = None) -> int:
    now = _now()
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO assessments (
                user_id, patient_name, age, pregnancies, glucose, blood_pressure,
                skin_thickness, insulin, bmi, diabetes_pedigree,
                risk_score, risk_category, report_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                data.get("patient_name", "Anonymous"),
                data["age"],
                data.get("pregnancies", 0),
                data["glucose"],
                data["blood_pressure"],
                data.get("skin_thickness"),
                data.get("insulin"),
                data["bmi"],
                data.get("diabetes_pedigree", 0.0),
                report["risk_score"],
                report["risk_category"],
                json.dumps(report),
                now,
            ),
        )
        return cursor.lastrowid


def get_assessment(assessment_id: int, user_id: int = None):
    with get_db() as conn:
        if user_id is not None:
            row = conn.execute(
                "SELECT * FROM assessments WHERE id = ? AND user_id = ?",
                (assessment_id, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["report"] = json.loads(result.pop("report_json"))
        return result


def get_user_assessments(user_id: int, limit: int = 50) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, patient_name, age, glucose, bmi, risk_score,
                      risk_category, created_at
               FROM assessments WHERE user_id = ?
               ORDER BY id DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def get_dashboard_stats(user_id: int) -> dict:
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM assessments WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        avg_risk = conn.execute(
            "SELECT AVG(risk_score) FROM assessments WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        categories = conn.execute(
            """SELECT risk_category, COUNT(*) as count
               FROM assessments WHERE user_id = ?
               GROUP BY risk_category""",
            (user_id,),
        ).fetchall()
        recent = conn.execute(
            """SELECT id, patient_name, risk_score, risk_category, created_at
               FROM assessments WHERE user_id = ?
               ORDER BY id DESC LIMIT 5""",
            (user_id,),
        ).fetchall()
        trend = conn.execute(
            """SELECT DATE(created_at) as day, AVG(risk_score) as avg_risk,
                      COUNT(*) as count
               FROM assessments WHERE user_id = ?
               GROUP BY DATE(created_at)
               ORDER BY day DESC LIMIT 14""",
            (user_id,),
        ).fetchall()

    return {
        "total_assessments": total or 0,
        "average_risk": round(avg_risk, 1) if avg_risk else 0,
        "categories": {row["risk_category"]: row["count"] for row in categories},
        "recent": [dict(row) for row in recent],
        "trend": [
            {
                "day": row["day"],
                "avg_risk": round(row["avg_risk"], 1),
                "count": row["count"],
            }
            for row in reversed(list(trend))
        ],
    }
