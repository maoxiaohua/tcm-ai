"""Stage-9 local sqlite access service for api.main compatibility."""

from __future__ import annotations

import os
import secrets
import sqlite3
import uuid
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.settings import PATHS

USER_HISTORY_DB_PATH = str(PATHS["data_dir"] / "user_history.sqlite")
LEARNING_DB_PATH = str(PATHS["data_dir"] / "learning_db.sqlite")


def _connect_user_history(*, row_factory: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(USER_HISTORY_DB_PATH)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def _derive_session_status(
    *,
    consultation_status: Optional[str],
    prescription_status: Optional[str],
    review_status: Optional[str],
    payment_status: Optional[str],
) -> str:
    normalized_consultation_status = (consultation_status or "").strip().lower()
    normalized_prescription_status = (prescription_status or "").strip().lower()
    normalized_review_status = (review_status or "").strip().lower()
    normalized_payment_status = (payment_status or "").strip().lower()

    if normalized_review_status in {"approved", "doctor_approved"} and normalized_payment_status in {"paid", "completed"}:
        return "completed"

    if normalized_review_status in {"rejected", "doctor_rejected"} or normalized_prescription_status in {"rejected", "doctor_rejected"}:
        return "review_rejected"

    if normalized_review_status in {"pending_review", "modified"} or normalized_prescription_status == "pending_review":
        return "pending_review"

    if normalized_payment_status in {"paid", "completed"}:
        return "pending_review"

    if normalized_payment_status == "pending" or normalized_prescription_status in {"ai_generated", "pending", "patient_confirmed"}:
        return "pending_payment"

    if normalized_consultation_status in {"completed", "pending_review", "pending_payment", "in_progress"}:
        return normalized_consultation_status

    return "in_progress"


def fetch_recent_learning_cases(limit: int) -> List[tuple]:
    """Fetch recent learning_cases rows from local learning sqlite."""
    if not os.path.exists(LEARNING_DB_PATH):
        return []

    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(LEARNING_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM learning_cases
            ORDER BY learned_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cursor.fetchall()
    finally:
        if conn:
            conn.close()


def get_user_info_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Read user info by token from unified/legacy session tables."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT us.user_id, uu.username, uu.email, ur.role_name
            FROM unified_sessions us
            JOIN unified_users uu ON us.user_id = uu.global_user_id
            LEFT JOIN user_roles_new ur ON uu.global_user_id = ur.user_id
                AND ur.is_active = 1 AND ur.is_primary = 1
            WHERE us.session_id = ? AND us.session_status = 'active'
              AND datetime(us.expires_at) > datetime('now')
            """,
            (token,),
        )
        result = cursor.fetchone()
        if result:
            user_id, username, email, role_name = result
            return {
                "user_id": user_id,
                "username": username,
                "email": email,
                "role": role_name.lower() if role_name else "patient",
            }

        cursor.execute(
            """
            SELECT user_id, role
            FROM user_sessions
            WHERE session_token = ? AND is_active = 1
              AND expires_at > datetime('now')
            """,
            (token,),
        )
        result = cursor.fetchone()
        if result:
            return {"user_id": result[0], "role": result[1]}

        return None
    finally:
        if conn:
            conn.close()


def register_email_user(
    *,
    email: str,
    password_hash: str,
    nickname: str,
    device_fingerprint: str,
) -> bool:
    """Register an email user; returns False when email already exists."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()

        cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return False

        now_iso = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO users (
                user_id, device_fingerprint, nickname, registration_type,
                created_at, last_active, is_verified, email, password_hash,
                role, is_active, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                device_fingerprint,
                nickname or email.split("@")[0],
                "email",
                now_iso,
                now_iso,
                1,
                email,
                password_hash,
                "patient",
                1,
                now_iso,
            ),
        )
        conn.commit()
        return True
    finally:
        if conn:
            conn.close()


def register_username_user(
    *,
    username: str,
    salted_password_hash: str,
    salt: str,
    device_fingerprint: str,
    registration_ip: str,
) -> Dict[str, Any]:
    """Register username in unified + legacy user tables."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()

        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        cursor.execute(
            "SELECT global_user_id FROM unified_users WHERE username = ?",
            (username,),
        )
        existing_unified_user = cursor.fetchone()

        if existing_user or existing_unified_user:
            return {"created": False}

        global_user_id = f"usr_{datetime.now().strftime('%Y%m%d')}_{secrets.token_hex(6)}"
        user_id = str(uuid.uuid4())
        now_iso = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO unified_users (
                global_user_id, username, display_name, password_hash, salt,
                account_status, created_at, updated_at, registration_source, registration_ip
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                global_user_id,
                username,
                username,
                salted_password_hash,
                salt,
                "active",
                now_iso,
                now_iso,
                "web_register",
                registration_ip,
            ),
        )

        cursor.execute(
            """
            INSERT INTO users (
                user_id, device_fingerprint, nickname, registration_type,
                created_at, last_active, is_verified, username, password_hash,
                role, is_active, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                device_fingerprint,
                username,
                "username",
                now_iso,
                now_iso,
                1,
                username,
                salted_password_hash,
                "patient",
                1,
                now_iso,
            ),
        )

        cursor.execute(
            """
            INSERT OR IGNORE INTO user_roles_new (
                user_id, role_name, is_active
            ) VALUES (?, ?, ?)
            """,
            (global_user_id, "patient", 1),
        )

        conn.commit()
        return {"created": True, "global_user_id": global_user_id}
    finally:
        if conn:
            conn.close()


def fetch_active_public_doctors(*, page: int, per_page: int) -> List[Dict[str, Any]]:
    """Fetch active doctors shown in the public list."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT id, name, license_no, speciality, hospital, created_at
            FROM doctors
            WHERE status = 'active' AND id IN (1, 4)
            ORDER BY
                CASE
                    WHEN id = 1 THEN 0
                    WHEN id = 4 THEN 1
                    ELSE 2
                END
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if conn:
            conn.close()


def fetch_admin_dashboard_stats() -> Dict[str, int]:
    """Fetch admin dashboard counters with table-fallback behavior."""
    conn: Optional[sqlite3.Connection] = None
    stats = {
        "total_users": 0,
        "active_doctors": 0,
        "today_consultations": 0,
        "pending_prescriptions": 0,
        "monthly_new_users": 0,
        "active_sessions": 0,
    }

    try:
        conn = _connect_user_history()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM unified_users WHERE account_status = 'active'")
        result = cursor.fetchone()
        stats["total_users"] = result[0] if result else 0

        cursor.execute(
            """
            SELECT COUNT(DISTINCT u.global_user_id)
            FROM unified_users u
            JOIN user_roles_new r ON u.global_user_id = r.user_id
            WHERE UPPER(r.role_name) = 'DOCTOR' AND r.is_active = 1
              AND u.account_status = 'active'
            """
        )
        result = cursor.fetchone()
        stats["active_doctors"] = result[0] if result else 0

        try:
            cursor.execute("SELECT COUNT(*) FROM consultations_new WHERE DATE(created_at) = DATE('now')")
            result = cursor.fetchone()
            stats["today_consultations"] = result[0] if result else 0
        except Exception:
            try:
                cursor.execute("SELECT COUNT(*) FROM conversation_metadata WHERE DATE(created_at) = DATE('now')")
                result = cursor.fetchone()
                stats["today_consultations"] = result[0] if result else 0
            except Exception:
                try:
                    cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE DATE(created_at) = DATE('now')")
                    result = cursor.fetchone()
                    stats["today_consultations"] = result[0] if result else 0
                except Exception:
                    stats["today_consultations"] = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE status = 'pending'")
            result = cursor.fetchone()
            stats["pending_prescriptions"] = result[0] if result else 0
        except Exception:
            stats["pending_prescriptions"] = 0

        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM unified_users
                WHERE DATE(created_at) >= DATE('now', 'start of month')
                """
            )
            result = cursor.fetchone()
            stats["monthly_new_users"] = result[0] if result else 0
        except Exception:
            stats["monthly_new_users"] = 0

        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM unified_sessions
                WHERE session_status = 'active' AND datetime(expires_at) > datetime('now')
                """
            )
            result = cursor.fetchone()
            stats["active_sessions"] = result[0] if result else 0
        except Exception:
            stats["active_sessions"] = 0

        return stats
    finally:
        if conn:
            conn.close()


def fetch_admin_users(*, page: int, per_page: int) -> Tuple[List[Dict[str, Any]], int]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT u.user_id, u.nickname, u.phone_number, u.created_at, u.last_active,
                   u.is_verified, COUNT(cm.conversation_id) as conversation_count
            FROM users u
            LEFT JOIN conversation_metadata cm ON u.user_id = cm.session_id
            GROUP BY u.user_id
            ORDER BY u.last_active DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        )
        rows = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        return rows, total
    finally:
        if conn:
            conn.close()


def fetch_admin_doctors(*, page: int, per_page: int) -> Tuple[List[Dict[str, Any]], int]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT id, name, license_no, phone, email, speciality, hospital,
                   status, created_at, last_login
            FROM doctors
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        )
        rows = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM doctors")
        total = cursor.fetchone()[0]
        return rows, total
    finally:
        if conn:
            conn.close()


def admin_add_doctor(doctor_data: Dict[str, Any]) -> Dict[str, Any]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM doctors WHERE license_no = ?",
            (doctor_data["license_no"],),
        )
        if cursor.fetchone():
            return {"status": "license_exists"}

        cursor.execute(
            """
            INSERT INTO doctors (name, license_no, phone, email, speciality, hospital,
                               introduction, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', datetime('now'), datetime('now'))
            """,
            (
                doctor_data["name"],
                doctor_data["license_no"],
                doctor_data.get("phone"),
                doctor_data.get("email"),
                doctor_data.get("speciality"),
                doctor_data.get("hospital"),
                doctor_data.get("introduction"),
            ),
        )
        doctor_id = cursor.lastrowid
        conn.commit()
        return {"status": "created", "doctor_id": doctor_id}
    finally:
        if conn:
            conn.close()


def admin_update_doctor(doctor_id: int, doctor_data: Dict[str, Any]) -> Dict[str, Any]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM doctors WHERE id = ?", (doctor_id,))
        if not cursor.fetchone():
            return {"status": "not_found"}

        update_fields = []
        values: List[Any] = []
        allowed_fields = [
            "name",
            "license_no",
            "phone",
            "email",
            "speciality",
            "hospital",
            "introduction",
            "status",
        ]
        for field in allowed_fields:
            if field in doctor_data:
                update_fields.append(f"{field} = ?")
                values.append(doctor_data[field])

        if not update_fields:
            return {"status": "no_fields"}

        if "license_no" in doctor_data:
            cursor.execute(
                "SELECT id FROM doctors WHERE license_no = ? AND id != ?",
                (doctor_data["license_no"], doctor_id),
            )
            if cursor.fetchone():
                return {"status": "license_exists"}

        update_fields.append("updated_at = datetime('now')")
        values.append(doctor_id)
        sql = f"UPDATE doctors SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(sql, values)
        conn.commit()
        return {"status": "updated"}
    finally:
        if conn:
            conn.close()


def admin_approve_doctor(doctor_id: int) -> Dict[str, str]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute("SELECT id, status FROM doctors WHERE id = ?", (doctor_id,))
        if not cursor.fetchone():
            return {"status": "not_found"}

        cursor.execute(
            """
            UPDATE doctors
            SET status = 'active', updated_at = datetime('now')
            WHERE id = ?
            """,
            (doctor_id,),
        )
        conn.commit()
        return {"status": "approved"}
    finally:
        if conn:
            conn.close()


def admin_reject_doctor(doctor_id: int) -> Dict[str, str]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM doctors WHERE id = ?", (doctor_id,))
        if not cursor.fetchone():
            return {"status": "not_found"}

        cursor.execute(
            """
            UPDATE doctors
            SET status = 'rejected', updated_at = datetime('now')
            WHERE id = ?
            """,
            (doctor_id,),
        )
        conn.commit()
        return {"status": "rejected"}
    finally:
        if conn:
            conn.close()


def fetch_admin_prescriptions(*, page: int, per_page: int) -> Tuple[List[Dict[str, Any]], int]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT p.*, d.name as doctor_name
            FROM prescriptions p
            LEFT JOIN doctors d ON p.doctor_id = d.id
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        )
        rows = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM prescriptions")
        total = cursor.fetchone()[0]
        return rows, total
    finally:
        if conn:
            conn.close()


def fetch_admin_prescription(prescription_id: int) -> Optional[Dict[str, Any]]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.*, d.name as doctor_name
            FROM prescriptions p
            LEFT JOIN doctors d ON p.doctor_id = d.id
            WHERE p.id = ?
            """,
            (prescription_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if conn:
            conn.close()


def fetch_admin_orders(*, page: int, per_page: int) -> Tuple[List[Dict[str, Any]], int]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT o.*, p.patient_name
            FROM orders o
            LEFT JOIN prescriptions p ON o.prescription_id = p.id
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        )
        rows = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM orders")
        total = cursor.fetchone()[0]
        return rows, total
    finally:
        if conn:
            conn.close()


def fetch_admin_logs(
    *,
    page: int,
    per_page: int,
    level: Optional[str],
    keyword: Optional[str],
    date: Optional[str],
) -> Tuple[List[Dict[str, Any]], int]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()

        query = """
            SELECT
                created_at as timestamp,
                'INFO' as level,
                resource_type || ':' || action as source,
                COALESCE(details, action || ' ' || COALESCE(resource_type, '')) as message
            FROM audit_logs
            UNION ALL
            SELECT
                event_timestamp as timestamp,
                CASE
                    WHEN risk_level = 'high' THEN 'ERROR'
                    WHEN risk_level = 'medium' THEN 'WARN'
                    ELSE 'INFO'
                END as level,
                audit_source as source,
                event_type || ': ' || COALESCE(event_details, '') as message
            FROM security_audit_logs
            WHERE 1=1
        """
        params: List[Any] = []
        conditions = []
        if level:
            conditions.append("level = ?")
            params.append(level)
        if keyword:
            conditions.append("(message LIKE ? OR source LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if date:
            conditions.append("DATE(timestamp) = ?")
            params.append(date)
        if conditions:
            query = f"SELECT * FROM ({query}) WHERE {' AND '.join(conditions)}"

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        logs = [
            {
                "timestamp": row[0],
                "level": row[1],
                "source": row[2],
                "message": row[3],
            }
            for row in rows
        ]

        count_query = """
            SELECT COUNT(*) FROM (
                SELECT created_at as timestamp, 'INFO' as level, resource_type as source, details as message FROM audit_logs
                UNION ALL
                SELECT event_timestamp as timestamp,
                    CASE WHEN risk_level = 'high' THEN 'ERROR' WHEN risk_level = 'medium' THEN 'WARN' ELSE 'INFO' END as level,
                    audit_source as source, event_type as message FROM security_audit_logs
            )
        """
        count_params: List[Any] = []
        if level or keyword or date:
            count_conditions = []
            if level:
                count_conditions.append("level = ?")
                count_params.append(level)
            if keyword:
                count_conditions.append("(message LIKE ? OR source LIKE ?)")
                count_params.extend([f"%{keyword}%", f"%{keyword}%"])
            if date:
                count_conditions.append("DATE(timestamp) = ?")
                count_params.append(date)
            count_query += " WHERE " + " AND ".join(count_conditions)

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        return logs, total
    finally:
        if conn:
            conn.close()


def fetch_admin_logs_for_export(
    *,
    level: Optional[str],
    keyword: Optional[str],
    date: Optional[str],
) -> List[tuple]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()

        query = """
            SELECT
                created_at as timestamp,
                'INFO' as level,
                resource_type || ':' || action as source,
                COALESCE(details, action || ' ' || COALESCE(resource_type, '')) as message
            FROM audit_logs
            UNION ALL
            SELECT
                event_timestamp as timestamp,
                CASE
                    WHEN risk_level = 'high' THEN 'ERROR'
                    WHEN risk_level = 'medium' THEN 'WARN'
                    ELSE 'INFO'
                END as level,
                audit_source as source,
                event_type || ': ' || COALESCE(event_details, '') as message
            FROM security_audit_logs
        """
        params: List[Any] = []
        conditions = []
        if level:
            conditions.append("level = ?")
            params.append(level)
        if keyword:
            conditions.append("(message LIKE ? OR source LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if date:
            conditions.append("DATE(timestamp) = ?")
            params.append(date)
        if conditions:
            query = f"SELECT * FROM ({query}) WHERE {' AND '.join(conditions)}"

        query += " ORDER BY timestamp DESC"
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        if conn:
            conn.close()


def update_user_session_activity(
    *,
    user_id: str,
    ip_address: str,
    user_agent: str,
    now_iso: str,
) -> None:
    """Upsert latest session activity for a user."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_token TEXT PRIMARY KEY,
                user_id TEXT,
                role TEXT,
                permissions TEXT,
                created_at TEXT,
                expires_at TEXT,
                ip_address TEXT,
                user_agent TEXT,
                last_activity TEXT,
                is_active INTEGER DEFAULT 1
            )
            """
        )

        cursor.execute(
            """
            SELECT session_token FROM user_sessions
            WHERE user_id = ?
            ORDER BY last_activity DESC LIMIT 1
            """,
            (user_id,),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE user_sessions
                SET last_activity = ?,
                    ip_address = ?,
                    user_agent = ?
                WHERE session_token = ?
                """,
                (now_iso, ip_address, user_agent, existing["session_token"]),
            )
        else:
            session_token = f"temp_{user_id}_{int(datetime.now().timestamp())}"
            cursor.execute(
                """
                INSERT INTO user_sessions
                (session_token, user_id, role, last_activity, ip_address, user_agent, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_token, user_id, "patient", now_iso, ip_address, user_agent, now_iso, 1),
            )

        conn.commit()
    finally:
        if conn:
            conn.close()


def fetch_latest_session_status(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch latest session status row for a user."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM user_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if conn:
            conn.close()


def delete_user_sessions(user_id: str) -> int:
    """Delete all sessions for a user."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM user_sessions
            WHERE user_id = ?
            """,
            (user_id,),
        )
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count
    finally:
        if conn:
            conn.close()


def fetch_active_sessions_last_day() -> List[Dict[str, Any]]:
    """Fetch active sessions within last 24 hours."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, COUNT(*) as session_count,
                   MAX(updated_at) as last_activity,
                   ip_address, user_agent
            FROM user_sessions
            WHERE datetime(updated_at) > datetime('now', '-1 day')
            GROUP BY user_id
            ORDER BY last_activity DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if conn:
            conn.close()


def _ensure_table_columns(cursor: sqlite3.Cursor, table_name: str, required_columns: Dict[str, str]) -> None:
    """Ensure sqlite table has required columns by ALTER fallback."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def log_security_event(
    *,
    event_type: str,
    user_id: Optional[str],
    severity: str,
    description: str,
    event_data_json: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
    created_at: str,
) -> int:
    """Insert security event and create alert for high severity events."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id TEXT,
                risk_level TEXT DEFAULT 'info',
                description TEXT,
                event_data TEXT,
                ip_address TEXT,
                user_agent TEXT,
                request_id TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        _ensure_table_columns(
            cursor,
            "security_events",
            {
                "risk_level": "TEXT DEFAULT 'info'",
                "severity": "TEXT DEFAULT 'info'",
            },
        )

        cursor.execute(
            """
            INSERT INTO security_events
            (event_type, user_id, risk_level, severity, description, event_data,
             ip_address, user_agent, request_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                user_id,
                severity,
                severity,
                description,
                event_data_json,
                ip_address,
                user_agent,
                request_id,
                created_at,
            ),
        )
        event_id = cursor.lastrowid

        if severity in ["error", "critical"]:
            try:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS security_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL,
                        alert_type TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        priority TEXT DEFAULT 'medium',
                        message TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        resolved_at TEXT,
                        FOREIGN KEY (event_id) REFERENCES security_events (id)
                    )
                    """
                )
                cursor.execute(
                    """
                    INSERT INTO security_alerts
                    (event_id, alert_type, priority, message, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        event_type,
                        "high" if severity == "critical" else "medium",
                        f"安全事件触发: {description}",
                        created_at,
                    ),
                )
            except Exception:
                # Keep endpoint behavior stable: alert creation failure should not fail event logging.
                pass

        conn.commit()
        return event_id
    finally:
        if conn:
            conn.close()


def fetch_security_events(
    *,
    limit: int,
    severity: Optional[str],
    event_type: Optional[str],
    user_id: Optional[str],
) -> List[Dict[str, Any]]:
    """Fetch security events with optional filters."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()

        conditions: List[str] = []
        params: List[Any] = []
        if severity:
            conditions.append("risk_level = ?")
            params.append(severity)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        cursor.execute(
            f"""
            SELECT * FROM security_events
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            params,
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if conn:
            conn.close()


def fetch_security_alerts(*, status: Optional[str]) -> List[Dict[str, Any]]:
    """Fetch security alerts joined with event metadata."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        where_clause = ""
        params: List[Any] = []
        if status:
            where_clause = "WHERE sa.status = ?"
            params.append(status)

        cursor.execute(
            f"""
            SELECT sa.*, se.event_type, se.user_id, se.description, se.ip_address
            FROM security_alerts sa
            JOIN security_events se ON sa.event_id = se.id
            {where_clause}
            ORDER BY sa.created_at DESC
            LIMIT 50
            """,
            params,
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if conn:
            conn.close()


def resolve_security_alert(*, alert_id: int, resolved_at: str) -> int:
    """Resolve one security alert; returns affected row count."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE security_alerts
            SET status = 'resolved', resolved_at = ?
            WHERE id = ?
            """,
            (resolved_at, alert_id),
        )
        affected = cursor.rowcount
        conn.commit()
        return affected
    finally:
        if conn:
            conn.close()


def fetch_security_statistics() -> Dict[str, Any]:
    """Fetch security statistics for dashboard."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT risk_level, COUNT(*) as count
            FROM security_events
            WHERE datetime(created_at) > datetime('now', '-7 days')
            GROUP BY risk_level
            """
        )
        severity_stats = {row["risk_level"]: row["count"] for row in cursor.fetchall() if row["risk_level"]}

        cursor.execute(
            """
            SELECT event_type, COUNT(*) as count
            FROM security_events
            WHERE datetime(created_at) > datetime('now', '-24 hours')
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 10
            """
        )
        event_type_stats = {row["event_type"]: row["count"] for row in cursor.fetchall() if row["event_type"]}

        cursor.execute(
            """
            SELECT COUNT(*) as pending_alerts
            FROM security_alerts
            WHERE status = 'pending'
            """
        )
        pending_alerts_row = cursor.fetchone()
        pending_alerts = pending_alerts_row["pending_alerts"] if pending_alerts_row else 0

        cursor.execute(
            """
            SELECT COUNT(*) as today_events
            FROM security_events
            WHERE DATE(created_at) = DATE('now')
            """
        )
        today_events_row = cursor.fetchone()
        today_events = today_events_row["today_events"] if today_events_row else 0

        return {
            "severity_stats": severity_stats,
            "event_type_stats": event_type_stats,
            "pending_alerts": pending_alerts,
            "today_events": today_events,
        }
    finally:
        if conn:
            conn.close()


def upsert_conversation_state(
    *,
    conversation_id: str,
    user_id: str,
    current_stage: str,
    updated_at: str,
) -> None:
    """Upsert conversation state row for websocket sync."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO conversation_states
            (conversation_id, user_id, current_stage, last_activity, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, user_id, current_stage, updated_at, updated_at),
        )
        conn.commit()
    finally:
        if conn:
            conn.close()


def fetch_latest_sync_state(*, user_id: str, recent_limit: int = 5) -> Dict[str, Any]:
    """Fetch latest conversation state and recent messages for websocket sync."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM conversation_states
            WHERE user_id = ? AND is_active = 1
            ORDER BY last_activity DESC LIMIT 1
            """,
            (user_id,),
        )
        latest_conversation = cursor.fetchone()

        cursor.execute(
            """
            SELECT message_content, sender, created_at
            FROM consultation_messages cm
            JOIN consultations c ON cm.consultation_id = c.uuid
            WHERE c.patient_id = ?
            ORDER BY cm.created_at DESC LIMIT ?
            """,
            (user_id, recent_limit),
        )
        recent_messages = [dict(row) for row in cursor.fetchall()]

        return {
            "conversation_state": dict(latest_conversation) if latest_conversation else None,
            "recent_messages": recent_messages,
        }
    finally:
        if conn:
            conn.close()


def sync_conversation_state_record(
    *,
    user_id: str,
    doctor_id: str,
    state_data: Dict[str, Any],
    device_info: Optional[Dict[str, Any]],
    ip_address: str,
    user_agent: str,
    now_iso: str,
) -> str:
    """Create or update conversation state and optional device record."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        conversation_id = f"conv_{user_id}_{doctor_id}_{int(datetime.now().timestamp())}"

        cursor.execute(
            """
            SELECT conversation_id, current_stage, last_activity
            FROM conversation_states
            WHERE user_id = ? AND doctor_id = ? AND is_active = 1
            ORDER BY last_activity DESC LIMIT 1
            """,
            (user_id, doctor_id),
        )
        existing = cursor.fetchone()

        if existing:
            conversation_id = existing["conversation_id"]
            cursor.execute(
                """
                UPDATE conversation_states
                SET current_stage = ?,
                    last_activity = ?,
                    turn_count = turn_count + 1,
                    symptoms_collected = ?,
                    stage_history = ?,
                    updated_at = ?
                WHERE conversation_id = ?
                """,
                (
                    state_data.get("currentState", "initial_inquiry"),
                    now_iso,
                    json.dumps(state_data.get("conversationData", {})),
                    json.dumps(state_data.get("stateHistory", [])),
                    now_iso,
                    conversation_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO conversation_states
                (conversation_id, user_id, doctor_id, current_stage, start_time,
                 last_activity, turn_count, symptoms_collected, stage_history,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    user_id,
                    doctor_id,
                    state_data.get("currentState", "initial_inquiry"),
                    now_iso,
                    now_iso,
                    1,
                    json.dumps(state_data.get("conversationData", {})),
                    json.dumps(state_data.get("stateHistory", [])),
                    now_iso,
                    now_iso,
                ),
            )

        if device_info:
            cursor.execute(
                """
                INSERT OR REPLACE INTO user_devices
                (user_id, device_fingerprint, ip_address, user_agent, last_used, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    user_id,
                    device_info.get("fingerprint", "unknown"),
                    ip_address,
                    user_agent,
                    now_iso,
                ),
            )

        conn.commit()
        return conversation_id
    finally:
        if conn:
            conn.close()


def _fetch_prescription_payment_info(
    cursor: sqlite3.Cursor,
    consultation_id: str,
) -> Optional[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT p.id, p.ai_prescription, p.status, p.payment_status,
               o.payment_status as order_payment_status
        FROM prescriptions p
        LEFT JOIN orders o ON p.id = o.prescription_id
        WHERE p.consultation_id = ?
        ORDER BY p.created_at DESC LIMIT 1
        """,
        (consultation_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None

    prescription_paid = row[3] in ("paid", "completed")
    order_paid = row[4] in ("paid", "completed")
    is_paid = prescription_paid or order_paid
    return {
        "prescription_id": row[0],
        "isPaid": is_paid,
        "hasActions": not is_paid,
    }


def fetch_conversation_history_bundle(
    *,
    user_id: str,
    doctor_id: Optional[str],
    sync_time: str,
) -> Dict[str, Any]:
    """Fetch conversation states, consultation records and flattened message history."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()

        if doctor_id:
            cursor.execute(
                """
                SELECT * FROM conversation_states
                WHERE user_id = ? AND doctor_id = ? AND is_active = 1
                ORDER BY last_activity DESC LIMIT 1
                """,
                (user_id, doctor_id),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM conversation_states
                WHERE user_id = ? AND is_active = 1
                ORDER BY last_activity DESC LIMIT 5
                """,
                (user_id,),
            )
        conversation_states = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT uuid, selected_doctor_id, symptoms_analysis, tcm_syndrome,
                   status, created_at, updated_at
            FROM consultations
            WHERE patient_id = ?
            ORDER BY created_at DESC LIMIT 10
            """,
            (user_id,),
        )
        consultation_records = [dict(row) for row in cursor.fetchall()]

        messages: List[Dict[str, Any]] = []
        try:
            if doctor_id:
                cursor.execute(
                    """
                    SELECT uuid, conversation_log, created_at, updated_at
                    FROM consultations
                    WHERE patient_id = ? AND selected_doctor_id = ?
                    ORDER BY created_at DESC LIMIT 20
                    """,
                    (user_id, doctor_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT uuid, conversation_log, selected_doctor_id, created_at, updated_at
                    FROM consultations
                    WHERE patient_id = ?
                    ORDER BY created_at DESC LIMIT 20
                    """,
                    (user_id,),
                )

            consultation_logs = cursor.fetchall()
            for log_row in consultation_logs:
                conversation_log = log_row[1]
                created_at = log_row[-2]
                if not conversation_log:
                    continue

                try:
                    log_data = json.loads(conversation_log)
                except json.JSONDecodeError:
                    continue

                if "conversation_history" in log_data:
                    conversation_history = log_data["conversation_history"]
                    if isinstance(conversation_history, list):
                        for conv_item in conversation_history:
                            if conv_item.get("patient_query"):
                                messages.append(
                                    {
                                        "type": "user",
                                        "content": conv_item["patient_query"],
                                        "time": conv_item.get("timestamp", created_at),
                                        "timestamp": conv_item.get("timestamp", created_at),
                                    }
                                )
                            if conv_item.get("ai_response"):
                                ai_message = {
                                    "type": "ai",
                                    "content": conv_item["ai_response"],
                                    "time": conv_item.get("timestamp", created_at),
                                    "timestamp": conv_item.get("timestamp", created_at),
                                }
                                if "处方" in conv_item["ai_response"] or "方剂" in conv_item["ai_response"]:
                                    prescription_info = _fetch_prescription_payment_info(cursor, log_row[0])
                                    if prescription_info:
                                        ai_message["prescriptionData"] = prescription_info
                                messages.append(ai_message)

                elif log_data.get("last_query") and log_data.get("last_response"):
                    messages.append(
                        {
                            "type": "user",
                            "content": log_data["last_query"],
                            "time": created_at,
                            "timestamp": created_at,
                        }
                    )
                    ai_message = {
                        "type": "ai",
                        "content": log_data["last_response"],
                        "time": created_at,
                        "timestamp": created_at,
                    }
                    if "处方" in log_data["last_response"] or "方剂" in log_data["last_response"]:
                        prescription_info = _fetch_prescription_payment_info(cursor, log_row[0])
                        if prescription_info:
                            ai_message["prescriptionData"] = prescription_info
                    messages.append(ai_message)

        except Exception:
            messages = []

        return {
            "conversation_states": conversation_states,
            "consultation_records": consultation_records,
            "messages": messages,
            "user_id": user_id,
            "sync_time": sync_time,
        }
    finally:
        if conn:
            conn.close()


def clear_conversation_history_records(
    *,
    user_id: str,
    doctor_id: str,
    clear_type: str,
) -> int:
    """Delete conversation-related records by clear type."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        deleted_count = 0

        if clear_type in ["all", "consultations"]:
            cursor.execute(
                """
                DELETE FROM consultations
                WHERE patient_id = ? AND selected_doctor_id = ?
                """,
                (user_id, doctor_id),
            )
            deleted_count += cursor.rowcount

        if clear_type in ["all", "conversation_states"]:
            cursor.execute(
                """
                DELETE FROM conversation_states
                WHERE user_id = ? AND doctor_id = ?
                """,
                (user_id, doctor_id),
            )
            deleted_count += cursor.rowcount

        if clear_type in ["all", "doctor_sessions"]:
            cursor.execute(
                """
                DELETE FROM doctor_sessions
                WHERE user_id = ? AND doctor_name = ?
                """,
                (user_id, doctor_id),
            )
            deleted_count += cursor.rowcount

        if clear_type in ["all", "prescriptions"]:
            cursor.execute(
                """
                DELETE FROM prescriptions
                WHERE patient_id = ? AND doctor_id = ? AND payment_status != 'paid'
                """,
                (user_id, doctor_id),
            )
            deleted_count += cursor.rowcount

        conn.commit()
        return deleted_count
    finally:
        if conn:
            conn.close()


def fetch_conversation_status(
    *,
    user_id: str,
    doctor_id: str,
) -> Optional[Dict[str, Any]]:
    """Fetch latest active conversation status for one user-doctor pair."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT cs.*,
                   COUNT(csh.id) as state_transitions,
                   MAX(csh.created_at) as last_transition_time
            FROM conversation_states cs
            LEFT JOIN conversation_stage_history csh ON cs.conversation_id = csh.conversation_id
            WHERE cs.user_id = ? AND cs.doctor_id = ? AND cs.is_active = 1
            GROUP BY cs.conversation_id
            ORDER BY cs.last_activity DESC LIMIT 1
            """,
            (user_id, doctor_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if conn:
            conn.close()


def cleanup_old_conversation_states(*, user_id: str, cutoff_date: str) -> int:
    """Deactivate old active conversation states for user."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE conversation_states
            SET is_active = 0
            WHERE user_id = ? AND last_activity < ? AND is_active = 1
            """,
            (user_id, cutoff_date),
        )
        affected = cursor.rowcount
        conn.commit()
        return affected
    finally:
        if conn:
            conn.close()


def create_user_backup_data(*, user_id: str, backup_time: str) -> Dict[str, Any]:
    """Build backup payload for user conversation-related tables."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        tables_to_backup = [
            ("conversation_states", "user_id"),
            ("consultations", "patient_id"),
            ("conversation_metadata", None),
            ("user_sessions", "user_id"),
        ]
        backup_data: Dict[str, Any] = {
            "user_id": user_id,
            "backup_time": backup_time,
            "data": {},
        }

        for table_name, user_field in tables_to_backup:
            if user_field:
                cursor.execute(f"SELECT * FROM {table_name} WHERE {user_field} = ?", (user_id,))
            else:
                cursor.execute(
                    """
                    SELECT cm.* FROM conversation_metadata cm
                    JOIN doctor_sessions ds ON cm.session_id = ds.session_id
                    WHERE ds.patient_id = ?
                    """,
                    (user_id,),
                )
            rows = cursor.fetchall()
            backup_data["data"][table_name] = [dict(row) for row in rows]

        return backup_data
    finally:
        if conn:
            conn.close()


def fetch_user_sessions_summary(*, user_id: Optional[str]) -> List[Dict[str, Any]]:
    """Fetch and format user session list for history page."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()

        if user_id:
            cursor.execute(
                """
                SELECT DISTINCT
                    c.uuid as session_id,
                    c.patient_id,
                    c.selected_doctor_id as doctor_name,
                    c.conversation_log,
                    c.status,
                    c.created_at,
                    c.updated_at,
                    p.id as prescription_id,
                    p.status as prescription_status,
                    p.review_status,
                    p.payment_status,
                    p.is_visible_to_patient
                FROM consultations c
                LEFT JOIN prescriptions p ON p.id = (
                    SELECT p2.id
                    FROM prescriptions p2
                    WHERE p2.consultation_id = c.uuid
                    ORDER BY
                        CASE
                            WHEN p2.review_status = 'approved' AND p2.payment_status IN ('paid', 'completed') THEN 0
                            WHEN p2.status IN ('approved', 'doctor_approved') AND p2.payment_status IN ('paid', 'completed') THEN 1
                            WHEN p2.review_status = 'pending_review' OR p2.status = 'pending_review' THEN 2
                            WHEN p2.payment_status IN ('paid', 'completed') THEN 3
                            WHEN p2.review_status IN ('rejected', 'doctor_rejected') OR p2.status IN ('rejected', 'doctor_rejected') THEN 4
                            ELSE 5
                        END,
                        COALESCE(p2.reviewed_at, p2.confirmed_at, p2.created_at) DESC,
                        p2.id DESC
                    LIMIT 1
                )
                WHERE c.patient_id = ?
                ORDER BY c.created_at DESC
                LIMIT 50
                """,
                (user_id,),
            )
        else:
            cursor.execute(
                """
                SELECT DISTINCT
                    c.uuid as session_id,
                    c.patient_id,
                    c.selected_doctor_id as doctor_name,
                    c.conversation_log,
                    c.status,
                    c.created_at,
                    c.updated_at,
                    p.id as prescription_id,
                    p.status as prescription_status,
                    p.review_status,
                    p.payment_status,
                    p.is_visible_to_patient
                FROM consultations c
                LEFT JOIN prescriptions p ON p.id = (
                    SELECT p2.id
                    FROM prescriptions p2
                    WHERE p2.consultation_id = c.uuid
                    ORDER BY
                        CASE
                            WHEN p2.review_status = 'approved' AND p2.payment_status IN ('paid', 'completed') THEN 0
                            WHEN p2.status IN ('approved', 'doctor_approved') AND p2.payment_status IN ('paid', 'completed') THEN 1
                            WHEN p2.review_status = 'pending_review' OR p2.status = 'pending_review' THEN 2
                            WHEN p2.payment_status IN ('paid', 'completed') THEN 3
                            WHEN p2.review_status IN ('rejected', 'doctor_rejected') OR p2.status IN ('rejected', 'doctor_rejected') THEN 4
                            ELSE 5
                        END,
                        COALESCE(p2.reviewed_at, p2.confirmed_at, p2.created_at) DESC,
                        p2.id DESC
                    LIMIT 1
                )
                ORDER BY c.created_at DESC
                LIMIT 50
                """
            )

        sessions_data = cursor.fetchall()
        doctor_names = {
            "jin_daifu": "金大夫",
            "ye_tianshi": "叶天士",
            "zhang_zhongjing": "张仲景",
            "li_dongyuan": "李东垣",
            "liu_duzhou": "刘渡舟",
            "zheng_qin_an": "郑钦安",
        }

        sessions: List[Dict[str, Any]] = []
        seen_session_ids = set()
        for row in sessions_data:
            try:
                session_id = row["session_id"]
                if not session_id or session_id in seen_session_ids:
                    continue
                seen_session_ids.add(session_id)

                chief_complaint = "问诊记录"
                diagnosis_summary = "问诊记录"
                prescription_given = "未知"
                has_prescription = bool(row["prescription_id"])
                message_count = 1

                if row["conversation_log"]:
                    try:
                        log_data = json.loads(row["conversation_log"])
                        if isinstance(log_data, dict):
                            conversation_history = log_data.get("conversation_history", [])
                            if conversation_history and len(conversation_history) > 0:
                                message_count = len(conversation_history)
                                for item in conversation_history:
                                    if item.get("patient_query"):
                                        chief_complaint = item["patient_query"][:50] + (
                                            "..." if len(item["patient_query"]) > 50 else ""
                                        )
                                        break
                                    elif item.get("type") == "user" and item.get("content"):
                                        chief_complaint = item["content"][:50] + (
                                            "..." if len(item["content"]) > 50 else ""
                                        )
                                        break

                                for item in conversation_history:
                                    ai_response = item.get("ai_response")
                                    if not ai_response and item.get("type") == "ai":
                                        ai_response = item.get("content")
                                    if ai_response:
                                        if "prescription-locked" in ai_response or "<div" in ai_response:
                                            diagnosis_summary = "【包含处方信息】"
                                            break

                                        if "辨证分析" in ai_response or "证" in ai_response or "诊断" in ai_response:
                                            if "【辨证分析】" in ai_response:
                                                start = ai_response.find("【辨证分析】")
                                                end = ai_response.find("【", start + 1)
                                                if end == -1:
                                                    end = ai_response.find("---", start)
                                                if end == -1:
                                                    end = start + 200
                                                diagnosis_content = ai_response[start:end].strip()
                                                diagnosis_summary = diagnosis_content[:100] + (
                                                    "..." if len(diagnosis_content) > 100 else ""
                                                )
                                            else:
                                                import re

                                                pattern = r"([^。]*?证[^。]*?)"
                                                matches = re.findall(pattern, ai_response)
                                                if matches:
                                                    diagnosis_summary = matches[0][:50] + (
                                                        "..." if len(matches[0]) > 50 else ""
                                                    )
                                        break
                            else:
                                if "last_query" in log_data:
                                    chief_complaint = log_data["last_query"][:50] + (
                                        "..." if len(log_data["last_query"]) > 50 else ""
                                    )
                                if "last_response" in log_data:
                                    response = log_data["last_response"]
                                    if "证" in response or "诊断" in response:
                                        import re

                                        pattern = r"([^。]*?证[^。]*?)"
                                        matches = re.findall(pattern, response)
                                        if matches:
                                            diagnosis_summary = matches[0][:30] + (
                                                "..." if len(matches[0]) > 30 else ""
                                            )
                        elif isinstance(log_data, list) and len(log_data) > 0:
                            user_messages = [msg for msg in log_data if msg.get("type") == "user"]
                            ai_messages = [msg for msg in log_data if msg.get("type") == "ai"]

                            if user_messages:
                                first_user_msg = user_messages[0]
                                if "content" in first_user_msg:
                                    chief_complaint = first_user_msg["content"][:50] + (
                                        "..." if len(first_user_msg["content"]) > 50 else ""
                                    )
                            elif ai_messages:
                                first_ai_msg = ai_messages[0]
                                if "content" in first_ai_msg:
                                    content = first_ai_msg["content"]
                                    if not any(
                                        keyword in content
                                        for keyword in ["您好", "欢迎", "请问", "能否", "什么", "如何"]
                                    ):
                                        chief_complaint = content[:50] + ("..." if len(content) > 50 else "")

                            if ai_messages:
                                for ai_msg in ai_messages:
                                    if ai_msg.get("content"):
                                        ai_content = ai_msg["content"]
                                        if "prescription-locked" in ai_content or "<div" in ai_content:
                                            diagnosis_summary = "【包含处方信息】"
                                            break
                                        if "辨证分析" in ai_content or "证" in ai_content or "诊断" in ai_content:
                                            if "【辨证分析】" in ai_content:
                                                start = ai_content.find("【辨证分析】")
                                                end = ai_content.find("【", start + 1)
                                                if end == -1:
                                                    end = ai_content.find("---", start)
                                                if end == -1:
                                                    end = start + 200
                                                diagnosis_content = ai_content[start:end].strip()
                                                diagnosis_summary = diagnosis_content[:100] + (
                                                    "..." if len(diagnosis_content) > 100 else ""
                                                )
                                            break

                            message_count = len(log_data)
                            if message_count == 0 or (
                                chief_complaint == "问诊记录" and diagnosis_summary == "问诊记录"
                            ):
                                continue
                    except Exception:
                        pass

                session_status = _derive_session_status(
                    consultation_status=row["status"],
                    prescription_status=row["prescription_status"],
                    review_status=row["review_status"],
                    payment_status=row["payment_status"],
                )
                if has_prescription:
                    payment_status = row["payment_status"]
                    prescription_status = row["prescription_status"]
                    review_status = row["review_status"]

                    if review_status == "approved":
                        prescription_given = "已开处方（审核通过）"
                    elif review_status in ("pending_review", "modified") or prescription_status == "pending_review":
                        prescription_given = "已开处方（等待医生审核）"
                    elif review_status in ("rejected", "doctor_rejected") or prescription_status in ("rejected", "doctor_rejected"):
                        prescription_given = "已开处方（审核未通过）"
                    elif payment_status in ("paid", "completed"):
                        prescription_given = "已开处方（已支付）"
                    elif payment_status == "pending" or prescription_status in ("ai_generated", "patient_confirmed", "pending"):
                        prescription_given = "已开处方（待支付）"
                    else:
                        prescription_given = "已开处方"

                sessions.append(
                    {
                        "session_id": session_id,
                        "doctor_name": row["doctor_name"],
                        "doctor_display_name": doctor_names.get(row["doctor_name"], row["doctor_name"]),
                        "chief_complaint": chief_complaint,
                        "session_count": 1,
                        "message_count": message_count,
                        "messages": [],
                        "status": session_status,
                        "session_status": session_status,
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "diagnosis_summary": diagnosis_summary,
                        "prescription_given": prescription_given,
                        "has_prescription": has_prescription,
                    }
                )
            except Exception:
                continue

        return sessions
    finally:
        if conn:
            conn.close()


def fetch_conversation_detail_data(session_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch one conversation detail with normalized history and prescription info."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        params: List[Any] = [session_id]
        user_filter = ""
        if user_id:
            user_filter = " AND c.patient_id = ? "
            params.append(user_id)

        cursor.execute(
            f"""
            SELECT
                c.*,
                d.name as doctor_display_name,
                p.id as prescription_id,
                p.ai_prescription,
                p.status as prescription_status,
                p.review_status,
                p.payment_status
            FROM consultations c
            LEFT JOIN doctors d ON (
                (c.selected_doctor_id = 'jin_daifu' AND d.id = 1) OR
                (c.selected_doctor_id = 'ye_tianshi' AND d.id = 2) OR
                (c.selected_doctor_id = 'zhang_zhongjing' AND d.id = 4) OR
                (c.selected_doctor_id = 'li_dongyuan' AND d.id = 3) OR
                (c.selected_doctor_id = 'liu_duzhou' AND d.id = 5) OR
                (c.selected_doctor_id = 'zheng_qin_an' AND d.id = 6)
            )
            LEFT JOIN prescriptions p ON p.id = (
                SELECT p2.id
                FROM prescriptions p2
                WHERE p2.consultation_id = c.uuid
                ORDER BY
                    CASE
                        WHEN p2.review_status = 'approved' AND p2.payment_status IN ('paid', 'completed') THEN 0
                        WHEN p2.status IN ('approved', 'doctor_approved') AND p2.payment_status IN ('paid', 'completed') THEN 1
                        WHEN p2.review_status = 'pending_review' OR p2.status = 'pending_review' THEN 2
                        WHEN p2.payment_status IN ('paid', 'completed') THEN 3
                        WHEN p2.review_status IN ('rejected', 'doctor_rejected') OR p2.status IN ('rejected', 'doctor_rejected') THEN 4
                        ELSE 5
                    END,
                    COALESCE(p2.reviewed_at, p2.confirmed_at, p2.created_at) DESC,
                    p2.id DESC
                LIMIT 1
            )
            WHERE c.uuid = ?
            {user_filter}
            """,
            tuple(params),
        )
        row = cursor.fetchone()
        if not row:
            return None

        try:
            conversation_log = json.loads(row["conversation_log"]) if row["conversation_log"] else {}
        except json.JSONDecodeError:
            conversation_log = {}

        conversation_history: List[Dict[str, Any]] = []
        chief_complaint = "未记录"
        diagnosis_summary = "问诊记录"
        prescription_given = "未知"
        has_prescription = bool(row["prescription_id"])

        if isinstance(conversation_log, dict):
            conversation_history = conversation_log.get("conversation_history", [])
        elif isinstance(conversation_log, list):
            conversation_history = []
            user_messages = [msg for msg in conversation_log if msg.get("type") == "user"]
            ai_messages = [msg for msg in conversation_log if msg.get("type") == "ai"]
            for i, user_msg in enumerate(user_messages):
                item = {"patient_query": user_msg.get("content", "")}
                if i < len(ai_messages):
                    item["ai_response"] = ai_messages[i].get("content", "")
                conversation_history.append(item)

        if conversation_history and len(conversation_history) > 0:
            for item in conversation_history:
                if item.get("patient_query"):
                    chief_complaint = (
                        item["patient_query"][:50] + "..."
                        if len(item["patient_query"]) > 50
                        else item["patient_query"]
                    )
                    break

            for item in conversation_history:
                if item.get("ai_response"):
                    ai_response = item["ai_response"]
                    if "prescription-locked" in ai_response or "<div" in ai_response:
                        diagnosis_summary = "【此问诊包含处方信息，请在智能问诊页面查看完整内容】"
                        break

                    if "辨证分析" in ai_response or "证" in ai_response or "诊断" in ai_response:
                        if "【辨证分析】" in ai_response:
                            start = ai_response.find("【辨证分析】")
                            end = ai_response.find("【", start + 1)
                            if end == -1:
                                end = ai_response.find("---", start)
                            if end == -1:
                                end = start + 300
                            diagnosis_content = ai_response[start:end].strip()
                            diagnosis_summary = diagnosis_content[:200] + (
                                "..." if len(diagnosis_content) > 200 else ""
                            )
                        else:
                            import re

                            pattern = r"([^。]*?证[^。]*?)"
                            matches = re.findall(pattern, ai_response)
                            if matches:
                                diagnosis_summary = matches[0][:50] + (
                                    "..." if len(matches[0]) > 50 else ""
                                )
                    break
        else:
            if isinstance(conversation_log, dict) and conversation_log.get("last_query"):
                chief_complaint = (
                    conversation_log["last_query"][:50] + "..."
                    if len(conversation_log["last_query"]) > 50
                    else conversation_log["last_query"]
                )

        detail_status = _derive_session_status(
            consultation_status=row["status"],
            prescription_status=row["prescription_status"],
            review_status=row["review_status"],
            payment_status=row["payment_status"],
        )

        if has_prescription:
            if row["review_status"] in ("approved", "doctor_approved") and row["payment_status"] in ("paid", "completed"):
                prescription_given = "已开处方（审核通过）"
            elif row["prescription_status"] == "doctor_approved":
                prescription_given = "已开处方（医生审核完成）"
            elif row["prescription_status"] == "doctor_modified":
                prescription_given = "已开处方（经医生修改）"
            elif row["prescription_status"] == "pending_review":
                prescription_given = "已开处方（等待医生审核，请勿配药）"
            elif row["prescription_status"] == "ai_generated":
                prescription_given = "已开处方（待支付解锁）"
            elif row["prescription_status"] == "paid":
                prescription_given = "已开处方（已支付）"
            elif row["prescription_status"] == "pending":
                prescription_given = "已开处方（待支付）"
            else:
                prescription_given = "已开处方"

        return {
            "session_id": session_id,
            "doctor_name": row["doctor_display_name"] or row["selected_doctor_id"],
            "conversation_history": conversation_history,
            "chief_complaint": chief_complaint,
            "diagnosis_summary": diagnosis_summary,
            "prescription_given": prescription_given,
            "has_prescription": has_prescription,
            "status": detail_status,
            "session_status": detail_status,
            "created_at": row["created_at"],
            "prescription": {
                "exists": has_prescription,
                "content": row["ai_prescription"] if row["prescription_id"] else None,
                "status": row["prescription_status"] if row["prescription_id"] else None,
                "prescription_id": row["prescription_id"],
            },
        }
    finally:
        if conn:
            conn.close()


def clear_all_user_session_history() -> Dict[str, Any]:
    """Clear all session-related records and return stats."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        tables_to_clear = ["consultations", "prescriptions", "conversation_states", "doctor_sessions"]
        table_stats: Dict[str, int] = {}
        total_deleted = 0

        for table in tables_to_clear:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_stats[table] = count
            cursor.execute(f"DELETE FROM {table}")
            total_deleted += cursor.rowcount

        conn.commit()

        stats_message: List[str] = []
        table_name_map = {
            "consultations": "问诊记录",
            "prescriptions": "处方记录",
            "conversation_states": "对话状态",
            "doctor_sessions": "医生会话",
        }
        for table, count in table_stats.items():
            if count > 0:
                stats_message.append(f"{table_name_map.get(table, table)}: {count}条")
        detail_message = f"已清空历史数据 ({', '.join(stats_message)})" if stats_message else "无数据需要清空"

        return {
            "message": detail_message,
            "deleted_count": total_deleted,
            "table_stats": table_stats,
        }
    finally:
        if conn:
            conn.close()


def clear_user_session_history(user_id: str) -> Dict[str, Any]:
    """Clear one user's session-related records and return stats."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()

        table_stats: Dict[str, int] = {}

        cursor.execute("SELECT COUNT(*) FROM consultations WHERE patient_id = ?", (user_id,))
        table_stats["consultations"] = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT COUNT(*) FROM prescriptions
            WHERE patient_id = ?
               OR consultation_id IN (
                    SELECT uuid FROM consultations WHERE patient_id = ?
               )
            """,
            (user_id, user_id),
        )
        table_stats["prescriptions"] = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT COUNT(*) FROM conversation_states
            WHERE user_id = ?
               OR conversation_id IN (
                    SELECT uuid FROM consultations WHERE patient_id = ?
               )
            """,
            (user_id, user_id),
        )
        table_stats["conversation_states"] = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT COUNT(*) FROM doctor_sessions
            WHERE user_id = ?
               OR session_id IN (
                    SELECT uuid FROM consultations WHERE patient_id = ?
               )
            """,
            (user_id, user_id),
        )
        table_stats["doctor_sessions"] = cursor.fetchone()[0]

        cursor.execute(
            """
            DELETE FROM prescriptions
            WHERE patient_id = ?
               OR consultation_id IN (
                    SELECT uuid FROM consultations WHERE patient_id = ?
               )
            """,
            (user_id, user_id),
        )
        cursor.execute("DELETE FROM consultations WHERE patient_id = ?", (user_id,))
        cursor.execute(
            """
            DELETE FROM conversation_states
            WHERE user_id = ?
               OR conversation_id IN (
                    SELECT uuid FROM consultations WHERE patient_id = ?
               )
            """,
            (user_id, user_id),
        )
        cursor.execute(
            """
            DELETE FROM doctor_sessions
            WHERE user_id = ?
               OR session_id IN (
                    SELECT uuid FROM consultations WHERE patient_id = ?
               )
            """,
            (user_id, user_id),
        )

        total_deleted = sum(table_stats.values())
        conn.commit()

        stats_message: List[str] = []
        table_name_map = {
            "consultations": "问诊记录",
            "prescriptions": "处方记录",
            "conversation_states": "对话状态",
            "doctor_sessions": "医生会话",
        }
        for table, count in table_stats.items():
            if count > 0:
                stats_message.append(f"{table_name_map.get(table, table)}: {count}条")

        return {
            "success": True,
            "message": (
                f"已清空当前用户历史数据 ({', '.join(stats_message)})"
                if stats_message
                else "当前用户无历史数据需要清空"
            ),
            "deleted_count": total_deleted,
            "table_stats": table_stats,
        }
    finally:
        if conn:
            conn.close()


def fetch_admin_users_overview() -> List[Dict[str, Any]]:
    """Fetch unified users with merged active roles for admin list."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.global_user_id, u.username, u.display_name, u.email,
                   u.phone_number, u.account_status, u.created_at, u.last_login_at,
                   GROUP_CONCAT(r.role_name) as roles
            FROM unified_users u
            LEFT JOIN user_roles_new r ON u.global_user_id = r.user_id AND r.is_active = 1
            GROUP BY u.global_user_id
            ORDER BY u.created_at DESC
            """
        )

        users: List[Dict[str, Any]] = []
        for row in cursor.fetchall():
            users.append(
                {
                    "id": row["global_user_id"],
                    "username": row["username"],
                    "display_name": row["display_name"],
                    "email": row["email"] or "未设置",
                    "phone_number": row["phone_number"] or "未设置",
                    "account_status": row["account_status"],
                    "roles": row["roles"].split(",") if row["roles"] else [],
                    "created_at": row["created_at"],
                    "last_login_at": row["last_login_at"] or "从未登录",
                }
            )
        return users
    finally:
        if conn:
            conn.close()


def update_admin_user(
    *,
    user_id: str,
    user_data: Dict[str, Any],
    updated_at: str,
) -> Dict[str, Any]:
    """Update allowed unified user fields for admin endpoint."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute("SELECT global_user_id FROM unified_users WHERE global_user_id = ?", (user_id,))
        if not cursor.fetchone():
            return {"status": "not_found"}

        allowed_fields = ["username", "display_name", "email", "phone_number", "account_status"]
        update_fields: List[str] = []
        values: List[Any] = []
        for field in allowed_fields:
            value = user_data.get(field)
            if value is not None:
                # 对于有UNIQUE约束的字段，空字符串转为NULL，避免唯一约束冲突
                if field in ("email", "phone_number", "username") and isinstance(value, str) and value.strip() == "":
                    value = None
                update_fields.append(f"{field} = ?")
                values.append(value)

        if not update_fields:
            return {"status": "no_fields"}

        update_fields.append("updated_at = ?")
        values.append(updated_at)
        values.append(user_id)
        update_query = f"""
            UPDATE unified_users
            SET {', '.join(update_fields)}
            WHERE global_user_id = ?
        """
        cursor.execute(update_query, values)
        conn.commit()
        if cursor.rowcount == 0:
            return {"status": "failed"}
        return {"status": "updated"}
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def fetch_admin_user_identity(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch admin target user identity."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT global_user_id, username FROM unified_users WHERE global_user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if conn:
            conn.close()


def admin_update_user_password(
    *,
    user_id: str,
    password_hash: str,
    salt: str,
    changed_at: str,
) -> bool:
    """Update unified user password hash+salt."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE unified_users
            SET password_hash = ?, salt = ?, password_changed_at = ?,
                login_attempts = 0, locked_until = NULL
            WHERE global_user_id = ?
            """,
            (password_hash, salt, changed_at, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def fetch_admin_system_stats() -> Dict[str, Any]:
    """Fetch core system stats for admin dashboard endpoint."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        stats: Dict[str, Any] = {}

        cursor.execute("SELECT COUNT(*) FROM unified_users")
        stats["total_users"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM unified_users WHERE account_status = 'active'")
        stats["active_users"] = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT role_name, COUNT(*) as count
            FROM user_roles_new
            WHERE is_active = 1
            GROUP BY role_name
            """
        )
        stats["roles"] = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM unified_sessions WHERE session_status = 'active'")
        stats["active_sessions"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM prescriptions")
        stats["total_prescriptions"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM prescriptions WHERE status = 'pending'")
        stats["pending_prescriptions"] = cursor.fetchone()[0]

        return stats
    finally:
        if conn:
            conn.close()


def fetch_prescription_for_structured_edit(prescription_id: int) -> Optional[Dict[str, Any]]:
    """Fetch base prescription fields for structured edit flow."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history(row_factory=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ai_prescription, doctor_prescription, status, doctor_notes
            FROM prescriptions WHERE id = ?
            """,
            (prescription_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if conn:
            conn.close()


def apply_structured_prescription_edit(
    *,
    prescription_id: int,
    doctor_id: str,
    new_prescription: str,
    doctor_notes: Optional[str],
) -> None:
    """Persist structured prescription edit and review history."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE prescriptions
            SET doctor_prescription = ?,
                doctor_notes = ?,
                reviewed_at = datetime('now')
            WHERE id = ?
            """,
            (new_prescription, doctor_notes, prescription_id),
        )
        cursor.execute(
            """
            INSERT INTO prescription_review_history (
                prescription_id, doctor_id, action, modified_prescription,
                doctor_notes, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (prescription_id, doctor_id, "structured_edit", new_prescription, doctor_notes),
        )
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def switch_doctor_conversation(*, user_id: str, doctor_id: str) -> Dict[str, Any]:
    """Switch doctor conversation based on latest consultation/prescription state."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT uuid, conversation_log, created_at
            FROM consultations
            WHERE patient_id = ? AND selected_doctor_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id, doctor_id),
        )
        latest = cursor.fetchone()

        if latest:
            consultation_id = latest[0]
            conversation_log = latest[1]

            cursor.execute(
                """
                SELECT id, created_at
                FROM prescriptions
                WHERE consultation_id = ?
                LIMIT 1
                """,
                (consultation_id,),
            )
            prescription = cursor.fetchone()

            if prescription:
                new_id = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO consultations
                    (uuid, patient_id, selected_doctor_id, conversation_log, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        user_id,
                        doctor_id,
                        json.dumps(
                            {
                                "conversation_id": new_id,
                                "conversation_history": [],
                                "current_stage": "inquiry",
                                "confidence_score": 0,
                            }
                        ),
                        datetime.now().isoformat() + "Z",
                    ),
                )
                conn.commit()
                return {
                    "consultation_id": new_id,
                    "messages": [],
                    "is_new": True,
                    "reason": "previous_conversation_has_prescription",
                    "message": f"上次对话已完成（处方ID: {prescription[0]}），已开启新对话",
                }

            try:
                log_data = json.loads(conversation_log) if conversation_log else {}
                if isinstance(log_data, list):
                    conversation_history = log_data
                else:
                    conversation_history = log_data.get("conversation_history", [])

                messages = []
                for item in conversation_history:
                    if "type" in item and "content" in item:
                        messages.append(
                            {
                                "type": item["type"],
                                "content": item["content"],
                                "time": item.get("time", ""),
                                "timestamp": item.get("timestamp", 0),
                            }
                        )
                    else:
                        if "patient_query" in item:
                            messages.append(
                                {
                                    "type": "user",
                                    "content": item["patient_query"],
                                    "time": item.get("time", ""),
                                    "timestamp": item.get("timestamp", 0),
                                }
                            )
                        if "ai_response" in item:
                            messages.append(
                                {
                                    "type": "ai",
                                    "content": item["ai_response"],
                                    "time": item.get("time", ""),
                                    "timestamp": item.get("timestamp", 0),
                                }
                            )

                return {
                    "consultation_id": consultation_id,
                    "messages": messages,
                    "is_new": False,
                    "reason": "continue_unfinished_conversation",
                    "message": f"继续未完成的对话（{len(messages)}条消息）",
                }
            except json.JSONDecodeError:
                return {
                    "consultation_id": consultation_id,
                    "messages": [],
                    "is_new": False,
                    "reason": "continue_conversation_parse_error",
                    "message": "继续对话（历史消息解析失败）",
                }

        new_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO consultations
            (uuid, patient_id, selected_doctor_id, conversation_log, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                new_id,
                user_id,
                doctor_id,
                json.dumps(
                    {
                        "conversation_id": new_id,
                        "conversation_history": [],
                        "current_stage": "inquiry",
                        "confidence_score": 0,
                    }
                ),
                datetime.now().isoformat() + "Z",
            ),
        )
        conn.commit()
        return {
            "consultation_id": new_id,
            "messages": [],
            "is_new": True,
            "reason": "first_conversation_with_doctor",
            "message": "首次与该医生对话",
        }
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def fetch_conversation_info(*, consultation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch consultation info for specific user."""
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect_user_history()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                c.uuid,
                c.selected_doctor_id,
                c.conversation_log,
                c.created_at,
                p.id as prescription_id,
                p.status as prescription_status
            FROM consultations c
            LEFT JOIN prescriptions p ON c.uuid = p.consultation_id
            WHERE c.uuid = ? AND c.patient_id = ?
            """,
            (consultation_id, user_id),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "success": True,
            "consultation_id": row[0],
            "doctor_id": row[1],
            "created_at": row[3],
            "has_prescription": row[4] is not None,
            "prescription_id": row[4],
            "prescription_status": row[5],
        }
    finally:
        if conn:
            conn.close()
