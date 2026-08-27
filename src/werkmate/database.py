"""Lokale SQLite-Persistenz für Aufträge, Arbeitseinsätze und Korrekturen."""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 11


class WerkMateDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number TEXT NOT NULL UNIQUE,
                    die_number TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    original_quantity INTEGER NOT NULL CHECK(original_quantity > 0),
                    seconds_per_piece INTEGER NOT NULL CHECK(seconds_per_piece > 0),
                    note TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'offen',
                    is_temporary INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS work_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL REFERENCES orders(id),
                    shift_name TEXT,
                    shift_start TEXT,
                    shift_end TEXT,
                    quantity_to_process INTEGER NOT NULL CHECK(quantity_to_process > 0),
                    seconds_per_piece INTEGER NOT NULL CHECK(seconds_per_piece > 0),
                    actual_started_at TEXT NOT NULL,
                    reported_started_at TEXT NOT NULL,
                    target_end TEXT NOT NULL,
                    pause_seconds INTEGER NOT NULL DEFAULT 0,
                    actual_confirmed_at TEXT,
                    reported_ended_at TEXT,
                    completed_quantity INTEGER CHECK(completed_quantity >= 0),
                    reported_quantity INTEGER CHECK(reported_quantity >= 0),
                    session_kind TEXT NOT NULL DEFAULT 'work',
                    planned_seconds INTEGER,
                    note TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'laufend',
                    voided_previous_status TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS correction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    reason TEXT NOT NULL DEFAULT '',
                    changed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    die_number TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS standards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    die_id INTEGER NOT NULL REFERENCES dies(id),
                    operation_id INTEGER NOT NULL REFERENCES operations(id),
                    seconds_per_piece INTEGER NOT NULL CHECK(seconds_per_piece > 0),
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(die_id, operation_id)
                );

                CREATE TABLE IF NOT EXISTS shift_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reported_start TEXT NOT NULL,
                    shift_number INTEGER NOT NULL CHECK(shift_number BETWEEN 1 AND 3),
                    custom_shift_end TEXT,
                    status TEXT NOT NULL DEFAULT 'aktiv',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS shift_plan_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER NOT NULL REFERENCES shift_plans(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    order_id INTEGER NOT NULL REFERENCES orders(id),
                    mode TEXT NOT NULL,
                    value INTEGER,
                    start_override TEXT,
                    status TEXT NOT NULL DEFAULT 'offen',
                    session_id INTEGER REFERENCES work_sessions(id),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS shift_settings (
                    shift_number INTEGER PRIMARY KEY CHECK(shift_number BETWEEN 1 AND 3),
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    break_start TEXT NOT NULL,
                    break_end TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS session_extensions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES work_sessions(id),
                    previous_target_end TEXT NOT NULL,
                    new_target_end TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_order ON work_sessions(order_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_reported_start
                    ON work_sessions(reported_started_at);
                CREATE INDEX IF NOT EXISTS idx_corrections_entity
                    ON correction_log(entity_type, entity_id);
                CREATE INDEX IF NOT EXISTS idx_standards_die ON standards(die_id);
                CREATE INDEX IF NOT EXISTS idx_shift_plan_items_plan
                    ON shift_plan_items(plan_id, position);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(work_sessions)").fetchall()
            }
            if "shift_start" not in columns:
                connection.execute("ALTER TABLE work_sessions ADD COLUMN shift_start TEXT")
            if "shift_end" not in columns:
                connection.execute("ALTER TABLE work_sessions ADD COLUMN shift_end TEXT")
            if "reported_quantity" not in columns:
                connection.execute("ALTER TABLE work_sessions ADD COLUMN reported_quantity INTEGER")
                connection.execute(
                    "UPDATE work_sessions SET reported_quantity = completed_quantity "
                    "WHERE completed_quantity IS NOT NULL"
                )
            if "session_kind" not in columns:
                connection.execute(
                    "ALTER TABLE work_sessions ADD COLUMN session_kind TEXT NOT NULL DEFAULT 'work'"
                )
            if "planned_seconds" not in columns:
                connection.execute("ALTER TABLE work_sessions ADD COLUMN planned_seconds INTEGER")
            if "voided_previous_status" not in columns:
                connection.execute("ALTER TABLE work_sessions ADD COLUMN voided_previous_status TEXT")
            order_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(orders)").fetchall()
            }
            if "is_temporary" not in order_columns:
                connection.execute(
                    "ALTER TABLE orders ADD COLUMN is_temporary INTEGER NOT NULL DEFAULT 0"
                )
            plan_columns = {
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(shift_plan_items)"
                ).fetchall()
            }
            if "start_override" not in plan_columns:
                connection.execute("ALTER TABLE shift_plan_items ADD COLUMN start_override TEXT")
            shift_plan_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(shift_plans)").fetchall()
            }
            if "custom_shift_end" not in shift_plan_columns:
                connection.execute("ALTER TABLE shift_plans ADD COLUMN custom_shift_end TEXT")
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            now = self._now()
            defaults = (
                (1, "05:45", "13:45", "08:45", "09:03"),
                (2, "13:45", "21:45", "17:45", "18:03"),
                (3, "21:45", "05:45", "01:45", "02:03"),
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO shift_settings(
                    shift_number, start_time, end_time, break_start, break_end, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [(*item, now) for item in defaults],
            )

    def shift_settings(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM shift_settings ORDER BY shift_number"
            ).fetchall()
        return [dict(row) for row in rows]

    def save_shift_settings(self, settings: list[dict[str, Any]]) -> None:
        if {int(item["shift_number"]) for item in settings} != {1, 2, 3}:
            raise ValueError("Es müssen genau die drei Schichten angegeben werden.")
        from .timecalc import standard_shift

        for item in settings:
            try:
                values = tuple(
                    datetime.strptime(str(item[key]).strip(), "%H:%M").time()
                    for key in ("start_time", "end_time", "break_start", "break_end")
                )
                standard_shift(int(item["shift_number"]), date.today(), values)
            except ValueError as error:
                raise ValueError(
                    f"Schicht {item['shift_number']}: Zeiten bitte als HH:MM eingeben; "
                    "die Pause muss innerhalb der Schicht liegen."
                ) from error
        now = self._now()
        with self.connect() as connection:
            for item in settings:
                connection.execute(
                    """
                    UPDATE shift_settings SET start_time = ?, end_time = ?, break_start = ?,
                        break_end = ?, updated_at = ? WHERE shift_number = ?
                    """,
                    (
                        item["start_time"], item["end_time"], item["break_start"],
                        item["break_end"], now, int(item["shift_number"]),
                    ),
                )

    def save_shift_plan(
        self, *, reported_start: datetime, shift_number: int, items: list[dict[str, Any]],
        custom_shift_end: datetime | None = None,
    ) -> int:
        if not items:
            raise ValueError("Der Schichtplan enthält keine Aufträge.")
        if shift_number not in (1, 2, 3):
            raise ValueError("Ungültige Schichtnummer.")
        now = self._now()
        with self.connect() as connection:
            running_item = connection.execute(
                """
                SELECT spi.plan_id, spi.position
                FROM shift_plan_items spi JOIN shift_plans sp ON sp.id = spi.plan_id
                WHERE sp.status = 'aktiv' AND spi.status = 'laufend'
                ORDER BY spi.id DESC LIMIT 1
                """
            ).fetchone()
            if running_item is not None:
                plan_id = int(running_item["plan_id"])
                connection.execute(
                    "DELETE FROM shift_plan_items WHERE plan_id = ? AND status = 'offen'",
                    (plan_id,),
                )
                for offset, item in enumerate(items, start=1):
                    connection.execute(
                        """
                        INSERT INTO shift_plan_items(
                            plan_id, position, order_id, mode, value, start_override,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            plan_id, int(running_item["position"]) + offset,
                            int(item["order_id"]), str(item["mode"]), item.get("value"),
                            item.get("start_override").isoformat()
                            if isinstance(item.get("start_override"), datetime)
                            else item.get("start_override"), now, now,
                        ),
                    )
                connection.execute(
                    "UPDATE shift_plans SET shift_number = ?, custom_shift_end = ?, updated_at = ? WHERE id = ?",
                    (shift_number, custom_shift_end.isoformat() if custom_shift_end else None, now, plan_id),
                )
                return plan_id
            connection.execute(
                "UPDATE shift_plans SET status = 'ersetzt', updated_at = ? WHERE status = 'aktiv'",
                (now,),
            )
            cursor = connection.execute(
                "INSERT INTO shift_plans(reported_start, shift_number, custom_shift_end, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (reported_start.isoformat(), shift_number,
                 custom_shift_end.isoformat() if custom_shift_end else None, now, now),
            )
            plan_id = int(cursor.lastrowid)
            for position, item in enumerate(items, start=1):
                connection.execute(
                    """
                    INSERT INTO shift_plan_items(
                        plan_id, position, order_id, mode, value, start_override,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan_id, position, int(item["order_id"]), str(item["mode"]),
                        item.get("value"),
                        item.get("start_override").isoformat()
                        if isinstance(item.get("start_override"), datetime)
                        else item.get("start_override"),
                        now, now,
                    ),
                )
        return plan_id

    def active_shift_plan(self) -> dict[str, Any] | None:
        with self.connect() as connection:
            plan = connection.execute(
                "SELECT * FROM shift_plans WHERE status = 'aktiv' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if plan is None:
                return None
            rows = connection.execute(
                """
                SELECT spi.*, o.order_number, o.die_number, o.operation
                FROM shift_plan_items spi JOIN orders o ON o.id = spi.order_id
                WHERE spi.plan_id = ? ORDER BY spi.position
                """,
                (plan["id"],),
            ).fetchall()
        result = dict(plan)
        result["items"] = [dict(row) for row in rows]
        return result

    def link_shift_plan_session(self, item_id: int, session_id: int) -> None:
        now = self._now()
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE shift_plan_items SET status = 'laufend', session_id = ?, updated_at = ? "
                "WHERE id = ? AND status = 'offen'",
                (session_id, now, item_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Der Planpunkt ist nicht mehr offen.")

    def discard_shift_plan(self) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE shift_plans SET status = 'verworfen', updated_at = ? WHERE status = 'aktiv'",
                (self._now(),),
            )

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def create_order(
        self,
        *,
        order_number: str,
        die_number: str,
        operation: str,
        original_quantity: int,
        seconds_per_piece: int,
        note: str = "",
        is_temporary: bool = False,
    ) -> int:
        now = self._now()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO orders(
                    order_number, die_number, operation, original_quantity,
                    seconds_per_piece, note, is_temporary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_number.strip(), die_number.strip(), operation.strip(),
                    original_quantity, seconds_per_piece, note.strip(), int(is_temporary), now, now,
                ),
            )
            return int(cursor.lastrowid)

    def get_order(self, order_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT o.*,
                       COALESCE(SUM(CASE WHEN ws.status != 'storniert' THEN ws.completed_quantity END), 0) AS completed_quantity,
                       COALESCE(SUM(CASE WHEN ws.status != 'storniert' THEN ws.reported_quantity END), 0) AS reported_quantity,
                       o.original_quantity - COALESCE(SUM(CASE WHEN ws.status != 'storniert' THEN ws.completed_quantity END), 0)
                           AS open_quantity,
                       COALESCE(SUM(CASE WHEN ws.status != 'storniert' THEN ws.completed_quantity END), 0)
                           - COALESCE(SUM(CASE WHEN ws.status != 'storniert' THEN ws.reported_quantity END), 0) AS credit_quantity
                FROM orders o
                LEFT JOIN work_sessions ws ON ws.order_id = o.id
                WHERE o.id = ?
                GROUP BY o.id
                """,
                (order_id,),
            ).fetchone()
        return dict(row) if row else None

    def find_order(self, order_number: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id FROM orders WHERE order_number = ?", (order_number.strip(),)
            ).fetchone()
        return self.get_order(int(row["id"])) if row else None

    def list_orders(
        self, *, include_handed_off: bool = True, include_archived: bool = False
    ) -> list[dict[str, Any]]:
        conditions = []
        if not include_handed_off:
            conditions.append("status != 'abgegeben'")
        if not include_archived:
            conditions.append("status != 'archiviert'")
        conditions.append("is_temporary = 0")
        clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self.connect() as connection:
            ids = connection.execute(
                f"SELECT id FROM orders {clause} ORDER BY updated_at DESC"  # noqa: S608
            ).fetchall()
        return [order for row in ids if (order := self.get_order(int(row["id"]))) is not None]

    def start_session(
        self,
        *,
        order_id: int,
        shift_name: str | None,
        quantity_to_process: int,
        seconds_per_piece: int,
        actual_started_at: datetime,
        reported_started_at: datetime,
        target_end: datetime,
        pause_seconds: int,
        note: str = "",
        shift_start: datetime | None = None,
        shift_end: datetime | None = None,
        session_kind: str = "work",
        planned_seconds: int | None = None,
    ) -> int:
        order = self.get_order(order_id)
        if order is None:
            raise ValueError("Auftrag nicht gefunden.")
        if quantity_to_process <= 0:
            raise ValueError("Die Einsatzmenge muss größer als null sein.")
        available_quantity = (
            order["credit_quantity"] if session_kind == "credit" else order["open_quantity"]
        )
        if quantity_to_process > available_quantity:
            raise ValueError("Die Einsatzmenge überschreitet die verfügbare Auftragsmenge.")
        if self.active_session() is not None:
            raise ValueError("Es läuft bereits ein persönlicher Arbeitseinsatz.")
        now = self._now()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO work_sessions(
                    order_id, shift_name, shift_start, shift_end, session_kind, planned_seconds,
                    quantity_to_process, seconds_per_piece,
                    actual_started_at, reported_started_at, target_end,
                    pause_seconds, note, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id, shift_name,
                    shift_start.isoformat() if shift_start else None,
                    shift_end.isoformat() if shift_end else None,
                    session_kind, planned_seconds,
                    quantity_to_process, seconds_per_piece,
                    actual_started_at.isoformat(), reported_started_at.isoformat(),
                    target_end.isoformat(), pause_seconds, note.strip(), now, now,
                ),
            )
            return int(cursor.lastrowid)

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT ws.*, o.order_number, o.die_number, o.operation
                FROM work_sessions ws
                JOIN orders o ON o.id = ws.order_id
                WHERE ws.id = ?
                """,
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    def active_session(self) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id FROM work_sessions
                WHERE status IN ('laufend', 'sollzeit_erreicht', 'ueberzogen')
                ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
        return self.get_session(int(row["id"])) if row else None

    def complete_session(
        self,
        session_id: int,
        *,
        completed_quantity: int,
        reported_quantity: int | None = None,
        actual_confirmed_at: datetime,
        reported_ended_at: datetime,
        note: str = "",
    ) -> None:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("Arbeitseinsatz nicht gefunden.")
        if completed_quantity < 0:
            raise ValueError("Die fertiggemeldete Menge ist ungültig.")
        order = self.get_order(int(session["order_id"]))
        if order is None or completed_quantity > order["open_quantity"]:
            raise ValueError("Die Rückmeldung überschreitet die offene Auftragsmenge.")
        effective_reported = completed_quantity if reported_quantity is None else reported_quantity
        if effective_reported < 0:
            raise ValueError("Die betriebliche Rückmeldemenge ist ungültig.")
        available_to_report = int(order["credit_quantity"]) + completed_quantity
        if effective_reported > available_to_report:
            raise ValueError("Es können nicht mehr Stück rückgemeldet als bearbeitet werden.")

        now = self._now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE work_sessions
                SET completed_quantity = ?, reported_quantity = ?, actual_confirmed_at = ?,
                    reported_ended_at = ?, note = ?, status = 'abgeschlossen',
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    completed_quantity, effective_reported, actual_confirmed_at.isoformat(),
                    reported_ended_at.isoformat(), note.strip(), now, session_id,
                ),
            )
            totals = connection.execute(
                """
                SELECT o.original_quantity,
                       COALESCE(SUM(CASE WHEN ws.status != 'storniert' THEN ws.completed_quantity END), 0) AS completed
                FROM orders o LEFT JOIN work_sessions ws ON ws.order_id = o.id
                WHERE o.id = ? GROUP BY o.id
                """,
                (session["order_id"],),
            ).fetchone()
            status = (
                "vollstaendig_erledigt"
                if totals["completed"] >= totals["original_quantity"]
                else "teilweise_erledigt"
            )
            connection.execute(
                "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, session["order_id"]),
            )
            plan_item = connection.execute(
                "SELECT id, plan_id FROM shift_plan_items WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if plan_item is not None:
                connection.execute(
                    "UPDATE shift_plan_items SET status = 'erledigt', updated_at = ? WHERE id = ?",
                    (now, plan_item["id"]),
                )
                remaining = connection.execute(
                    "SELECT COUNT(*) AS amount FROM shift_plan_items "
                    "WHERE plan_id = ? AND status IN ('offen', 'laufend')",
                    (plan_item["plan_id"],),
                ).fetchone()["amount"]
                connection.execute(
                    "UPDATE shift_plans SET reported_start = ?, status = ?, updated_at = ? WHERE id = ?",
                    (
                        reported_ended_at.isoformat(),
                        "aktiv" if remaining else "abgeschlossen",
                        now,
                        plan_item["plan_id"],
                    ),
                )

    def cancel_session(self, session_id: int, *, reason: str = "Fehlstart") -> None:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("Arbeitseinsatz nicht gefunden.")
        if session["status"] not in ("laufend", "sollzeit_erreicht", "ueberzogen"):
            raise ValueError("Nur ein laufender Arbeitseinsatz kann abgebrochen werden.")
        now = self._now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE work_sessions
                SET status = 'abgebrochen', completed_quantity = 0,
                    actual_confirmed_at = ?, note = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, reason.strip(), now, session_id),
            )
            connection.execute(
                "UPDATE shift_plan_items SET status = 'offen', session_id = NULL, updated_at = ? "
                "WHERE session_id = ?",
                (now, session_id),
            )

    def extend_session(self, session_id: int, *, new_target_end: datetime, reason: str = "") -> None:
        session = self.get_session(session_id)
        if session is None or session["status"] not in ("laufend", "sollzeit_erreicht", "ueberzogen"):
            raise ValueError("Nur ein laufender Arbeitseinsatz kann verlängert werden.")
        previous = datetime.fromisoformat(str(session["target_end"]))
        now_local = datetime.now().astimezone().replace(tzinfo=None)
        if new_target_end <= now_local:
            raise ValueError("Die neue Endzeit muss in der Zukunft liegen.")
        if new_target_end <= previous:
            raise ValueError("Die neue Endzeit muss nach der bisherigen Endzeit liegen.")
        now = self._now()
        with self.connect() as connection:
            connection.execute(
                "UPDATE work_sessions SET target_end = ?, updated_at = ? WHERE id = ?",
                (new_target_end.isoformat(), now, session_id),
            )
            connection.execute(
                """
                INSERT INTO session_extensions(
                    session_id, previous_target_end, new_target_end, reason, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, previous.isoformat(), new_target_end.isoformat(), reason.strip(), now),
            )

    def session_extensions(self, session_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM session_extensions WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_field(
        self,
        entity_type: str,
        entity_id: int,
        field_name: str,
        new_value: Any,
        *,
        reason: str = "",
    ) -> None:
        allowed = {
            "order": {"die_number", "operation", "original_quantity", "note", "status"},
            "session": {
                "reported_started_at", "reported_ended_at", "completed_quantity", "note", "status"
            },
        }
        if entity_type not in allowed or field_name not in allowed[entity_type]:
            raise ValueError("Dieses Feld darf nicht über die Historie korrigiert werden.")
        table = "orders" if entity_type == "order" else "work_sessions"
        now = self._now()
        with self.connect() as connection:
            row = connection.execute(
                f"SELECT {field_name} FROM {table} WHERE id = ?",  # noqa: S608
                (entity_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Datensatz nicht gefunden.")
            old_value = row[field_name]
            connection.execute(
                f"UPDATE {table} SET {field_name} = ?, updated_at = ? WHERE id = ?",  # noqa: S608
                (new_value, now, entity_id),
            )
            connection.execute(
                """
                INSERT INTO correction_log(
                    entity_type, entity_id, field_name, old_value, new_value,
                    reason, changed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity_type, entity_id, field_name, json.dumps(old_value),
                    json.dumps(new_value), reason.strip(), now,
                ),
            )

    def correct_session(
        self,
        session_id: int,
        *,
        reported_started_at: datetime,
        reported_ended_at: datetime,
        completed_quantity: int,
        reported_quantity: int,
        note: str,
        reason: str,
    ) -> None:
        current = self.get_session(session_id)
        if current is None:
            raise ValueError("Rückmeldung nicht gefunden.")
        if current["status"] != "abgeschlossen":
            raise ValueError("Nur abgeschlossene Rückmeldungen können korrigiert werden.")
        if not reason.strip():
            raise ValueError("Bitte einen Grund für die Korrektur angeben.")
        if reported_ended_at < reported_started_at:
            raise ValueError("Die Abmeldezeit darf nicht vor der Anmeldezeit liegen.")
        if completed_quantity < 0 or reported_quantity < 0:
            raise ValueError("Stückzahlen dürfen nicht negativ sein.")
        if current["session_kind"] == "credit" and completed_quantity != 0:
            raise ValueError("Ein Guthabeneinsatz enthält keine neu bearbeiteten Stück.")

        now = self._now()
        with self.connect() as connection:
            totals = connection.execute(
                """
                SELECT o.original_quantity,
                       COALESCE(SUM(CASE WHEN ws.id != ? AND ws.status != 'storniert' THEN ws.completed_quantity END), 0)
                           AS other_completed,
                       COALESCE(SUM(CASE WHEN ws.id != ? AND ws.status != 'storniert' THEN ws.reported_quantity END), 0)
                           AS other_reported
                FROM orders o LEFT JOIN work_sessions ws ON ws.order_id = o.id
                WHERE o.id = ? GROUP BY o.id
                """,
                (session_id, session_id, current["order_id"]),
            ).fetchone()
            new_completed_total = int(totals["other_completed"]) + completed_quantity
            new_reported_total = int(totals["other_reported"]) + reported_quantity
            if new_completed_total > int(totals["original_quantity"]):
                raise ValueError("Die Korrektur überschreitet die gesamte Auftragsmenge.")
            if new_reported_total > new_completed_total:
                raise ValueError("Insgesamt können nicht mehr Stück gemeldet als bearbeitet sein.")

            old_start = datetime.fromisoformat(str(current["reported_started_at"]))
            old_target = datetime.fromisoformat(str(current["target_end"]))
            corrected_target = old_target + (reported_started_at - old_start)
            changes = {
                "reported_started_at": reported_started_at.isoformat(),
                "target_end": corrected_target.isoformat(),
                "reported_ended_at": reported_ended_at.isoformat(),
                "completed_quantity": completed_quantity,
                "reported_quantity": reported_quantity,
                "note": note.strip(),
            }
            for field_name, new_value in changes.items():
                old_value = current[field_name]
                if old_value == new_value:
                    continue
                connection.execute(
                    f"UPDATE work_sessions SET {field_name} = ?, updated_at = ? WHERE id = ?",  # noqa: S608
                    (new_value, now, session_id),
                )
                connection.execute(
                    """
                    INSERT INTO correction_log(
                        entity_type, entity_id, field_name, old_value, new_value,
                        reason, changed_at
                    ) VALUES ('session', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id, field_name, json.dumps(old_value), json.dumps(new_value),
                        reason.strip(), now,
                    ),
                )
            order_status = (
                "vollstaendig_erledigt"
                if new_completed_total >= int(totals["original_quantity"])
                else "teilweise_erledigt"
            )
            connection.execute(
                "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                (order_status, now, current["order_id"]),
            )

    def hand_off_order(self, order_id: int, *, reason: str = "") -> None:
        self.update_field("order", order_id, "status", "abgegeben", reason=reason)

    def resume_order(self, order_id: int) -> None:
        order = self.get_order(order_id)
        if order is None:
            raise ValueError("Auftrag nicht gefunden.")
        if order["open_quantity"] <= 0:
            raise ValueError("Der Auftrag besitzt keine offene Menge.")
        self.update_field(
            "order", order_id, "status", "teilweise_erledigt", reason="Erneut aufgenommen"
        )

    def duplicate_order(self, order_id: int, *, order_number: str | None = None) -> int:
        order = self.get_order(order_id)
        if order is None:
            raise ValueError("Auftrag nicht gefunden.")
        base = (order_number or f"{order['order_number']}-KOPIE").strip()
        candidate = base
        suffix = 2
        while self.find_order(candidate) is not None:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return self.create_order(
            order_number=candidate,
            die_number=str(order["die_number"]),
            operation=str(order["operation"]),
            original_quantity=int(order["original_quantity"]),
            seconds_per_piece=int(order["seconds_per_piece"]),
            note=str(order["note"]),
        )

    def archive_order(self, order_id: int) -> None:
        active = self.active_session()
        if active is not None and int(active["order_id"]) == order_id:
            raise ValueError("Ein laufender Auftrag kann nicht archiviert werden.")
        self.update_field("order", order_id, "status", "archiviert", reason="In Papierkorb verschoben")

    def restore_archived_order(self, order_id: int) -> None:
        order = self.get_order(order_id)
        if order is None or order["status"] != "archiviert":
            raise ValueError("Archivierter Auftrag nicht gefunden.")
        restored_status = (
            "vollstaendig_erledigt" if int(order["open_quantity"]) <= 0
            else "teilweise_erledigt" if int(order["completed_quantity"]) else "offen"
        )
        self.update_field("order", order_id, "status", restored_status, reason="Aus Papierkorb wiederhergestellt")

    def permanently_delete_archived_order(self, order_id: int) -> None:
        order = self.get_order(order_id)
        if order is None or order["status"] != "archiviert":
            raise ValueError("Nur archivierte Aufträge können endgültig gelöscht werden.")
        with self.connect() as connection:
            session_ids = [
                int(row["id"]) for row in connection.execute(
                    "SELECT id FROM work_sessions WHERE order_id = ?", (order_id,)
                ).fetchall()
            ]
            connection.execute("DELETE FROM shift_plan_items WHERE order_id = ?", (order_id,))
            for session_id in session_ids:
                connection.execute(
                    "DELETE FROM session_extensions WHERE session_id = ?", (session_id,)
                )
                connection.execute(
                    "DELETE FROM correction_log WHERE entity_type = 'session' AND entity_id = ?",
                    (session_id,),
                )
            connection.execute("DELETE FROM work_sessions WHERE order_id = ?", (order_id,))
            connection.execute(
                "DELETE FROM correction_log WHERE entity_type = 'order' AND entity_id = ?",
                (order_id,),
            )
            connection.execute("DELETE FROM orders WHERE id = ?", (order_id,))

    def void_session(self, session_id: int, *, reason: str) -> None:
        session = self.get_session(session_id)
        if session is None or session["status"] == "storniert":
            raise ValueError("Diese Rückmeldung kann nicht storniert werden.")
        if not reason.strip():
            raise ValueError("Bitte einen Stornierungsgrund angeben.")
        previous_status = str(session["status"])
        safe_previous = "abgebrochen" if previous_status in ("laufend", "sollzeit_erreicht", "ueberzogen") else previous_status
        now = self._now()
        with self.connect() as connection:
            connection.execute(
                "UPDATE work_sessions SET status = 'storniert', voided_previous_status = ?, "
                "updated_at = ? WHERE id = ?",
                (safe_previous, now, session_id),
            )
            connection.execute(
                """
                INSERT INTO correction_log(
                    entity_type, entity_id, field_name, old_value, new_value, reason, changed_at
                ) VALUES ('session', ?, 'status', ?, ?, ?, ?)
                """,
                (session_id, json.dumps(previous_status), json.dumps("storniert"), reason.strip(), now),
            )
            if previous_status in ("laufend", "sollzeit_erreicht", "ueberzogen"):
                connection.execute(
                    "UPDATE shift_plan_items SET status = 'offen', session_id = NULL, updated_at = ? "
                    "WHERE session_id = ?",
                    (now, session_id),
                )
        self._sync_order_status(int(session["order_id"]))

    def restore_voided_session(self, session_id: int) -> None:
        session = self.get_session(session_id)
        if session is None or session["status"] != "storniert":
            raise ValueError("Stornierte Rückmeldung nicht gefunden.")
        order = self.get_order(int(session["order_id"]))
        if order is None:
            raise ValueError("Auftrag nicht gefunden.")
        if int(order["completed_quantity"]) + int(session["completed_quantity"] or 0) > int(order["original_quantity"]):
            raise ValueError("Die Wiederherstellung würde die Auftragsmenge überschreiten.")
        restored_status = str(session.get("voided_previous_status") or "abgeschlossen")
        self.update_field(
            "session", session_id, "status", restored_status, reason="Stornierung aufgehoben"
        )
        self._sync_order_status(int(session["order_id"]))

    def permanently_delete_voided_session(self, session_id: int) -> None:
        session = self.get_session(session_id)
        if session is None or session["status"] != "storniert":
            raise ValueError("Nur stornierte Rückmeldungen können endgültig gelöscht werden.")
        with self.connect() as connection:
            connection.execute("DELETE FROM shift_plan_items WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM session_extensions WHERE session_id = ?", (session_id,))
            connection.execute(
                "DELETE FROM correction_log WHERE entity_type = 'session' AND entity_id = ?",
                (session_id,),
            )
            connection.execute("DELETE FROM work_sessions WHERE id = ?", (session_id,))
        self._sync_order_status(int(session["order_id"]))

    def _sync_order_status(self, order_id: int) -> None:
        order = self.get_order(order_id)
        if order is None or order["status"] == "archiviert":
            return
        status = (
            "vollstaendig_erledigt" if int(order["open_quantity"]) <= 0
            else "teilweise_erledigt" if int(order["completed_quantity"]) else "offen"
        )
        with self.connect() as connection:
            connection.execute(
                "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                (status, self._now(), order_id),
            )

    def update_order(
        self,
        order_id: int,
        *,
        order_number: str | None = None,
        die_number: str,
        operation: str,
        original_quantity: int,
        seconds_per_piece: int,
        note: str,
        reason: str = "Manuelle Auftragskorrektur",
    ) -> None:
        current = self.get_order(order_id)
        if current is None:
            raise ValueError("Auftrag nicht gefunden.")
        if not die_number.strip() or not operation.strip():
            raise ValueError("Gesenknummer und Arbeitsgang dürfen nicht leer sein.")
        if original_quantity < int(current["completed_quantity"]):
            raise ValueError("Die Gesamtmenge darf nicht kleiner als die bereits gemeldete Menge sein.")
        if original_quantity <= 0 or seconds_per_piece <= 0:
            raise ValueError("Menge und Vorgabezeit müssen größer als null sein.")

        resolved_number = (order_number or str(current["order_number"])).strip()
        if not resolved_number:
            raise ValueError("Die Auftragsnummer darf nicht leer sein.")
        existing = self.find_order(resolved_number)
        if existing is not None and int(existing["id"]) != order_id:
            raise ValueError("Diese Auftragsnummer ist bereits gespeichert.")

        changes = {
            "order_number": resolved_number,
            "die_number": die_number.strip(),
            "operation": operation.strip(),
            "original_quantity": original_quantity,
            "seconds_per_piece": seconds_per_piece,
            "note": note.strip(),
        }
        now = self._now()
        with self.connect() as connection:
            for field_name, new_value in changes.items():
                old_value = current[field_name]
                if old_value == new_value:
                    continue
                connection.execute(
                    f"UPDATE orders SET {field_name} = ?, updated_at = ? WHERE id = ?",  # noqa: S608
                    (new_value, now, order_id),
                )
                connection.execute(
                    """
                    INSERT INTO correction_log(
                        entity_type, entity_id, field_name, old_value, new_value,
                        reason, changed_at
                    ) VALUES ('order', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id, field_name, json.dumps(old_value), json.dumps(new_value),
                        reason.strip(), now,
                    ),
                )

    def history(
        self,
        *,
        limit: int = 100,
        search: str = "",
        status: str = "",
        include_voided: bool = False,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        parameters: list[Any] = []
        if search.strip():
            term = f"%{search.strip()}%"
            conditions.append(
                "(o.order_number LIKE ? OR o.die_number LIKE ? OR o.operation LIKE ? "
                "OR ws.note LIKE ? OR o.note LIKE ?)"
            )
            parameters.extend([term] * 5)
        if status.strip():
            conditions.append("ws.status = ?")
            parameters.append(status.strip())
        elif not include_voided:
            conditions.append("ws.status != 'storniert'")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        parameters.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT ws.*, o.order_number, o.die_number, o.operation,
                       o.original_quantity
                FROM work_sessions ws
                JOIN orders o ON o.id = ws.order_id
                {where}
                ORDER BY ws.reported_started_at DESC, ws.id DESC
                LIMIT ?
                """,  # noqa: S608 -- where contains only fixed fragments
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def corrections(self, entity_type: str, entity_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM correction_log
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY changed_at, id
                """,
                (entity_type, entity_id),
            ).fetchall()
        return [dict(row) for row in rows]

    def backup_to(self, destination: str | Path) -> Path:
        """Erzeugt mit SQLite eine konsistente lokale Sicherungskopie."""
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.path)
        target = sqlite3.connect(destination_path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return destination_path

    def restore_from(self, source_path: str | Path) -> None:
        source_path = Path(source_path)
        if not source_path.is_file():
            raise ValueError("Die ausgewählte Sicherungsdatei wurde nicht gefunden.")
        source = sqlite3.connect(source_path)
        source.row_factory = sqlite3.Row
        try:
            integrity = source.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError("Die Sicherungsdatei ist beschädigt.")
            tables = {
                row["name"] for row in source.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if not {"metadata", "orders", "work_sessions"} <= tables:
                raise ValueError("Die Datei ist keine gültige WerkMate-Sicherung.")
            target = sqlite3.connect(self.path)
            try:
                source.backup(target)
            finally:
                target.close()
        finally:
            source.close()
        self.initialize()

    def export_csv(self, destination_directory: str | Path) -> tuple[Path, Path]:
        directory = Path(destination_directory)
        directory.mkdir(parents=True, exist_ok=True)
        orders_path = directory / "WerkMate-Auftraege.csv"
        history_path = directory / "WerkMate-Rueckmeldungen.csv"
        order_fields = (
            "Auftragsnummer", "Gesenknummer", "Arbeitsgang", "Gesamtmenge",
            "Bearbeitet", "Rueckgemeldet", "Guthaben", "Offen", "Minuten_pro_Stueck",
            "Status", "Notiz",
        )
        with orders_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(order_fields)
            for item in self.list_orders():
                writer.writerow((
                    item["order_number"], item["die_number"], item["operation"],
                    item["original_quantity"], item["completed_quantity"],
                    item["reported_quantity"], item["credit_quantity"], item["open_quantity"],
                    str(item["seconds_per_piece"] / 60).replace(".", ","),
                    item["status"], item["note"],
                ))
        history_fields = (
            "ID", "Auftragsnummer", "Gesenknummer", "Arbeitsgang", "Anmeldung",
            "Geplantes_Ende", "Abmeldung", "Bearbeitet", "Rueckgemeldet", "Planmenge",
            "Vorgabe_Sekunden_pro_Stueck", "Art", "Status", "Notiz",
        )
        with history_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(history_fields)
            for item in self.history(limit=1_000_000, include_voided=True):
                writer.writerow((
                    item["id"], item["order_number"], item["die_number"], item["operation"],
                    item["reported_started_at"], item["target_end"], item["reported_ended_at"],
                    item["completed_quantity"], item["reported_quantity"],
                    item["quantity_to_process"], item["seconds_per_piece"],
                    item["session_kind"], item["status"], item["note"],
                ))
        return orders_path, history_path

    def save_standard(
        self,
        *,
        die_number: str,
        operation_code: str,
        operation_name: str,
        seconds_per_piece: int,
        die_description: str = "",
        die_note: str = "",
    ) -> int:
        die_number = die_number.strip()
        operation_code = operation_code.strip().upper()
        operation_name = operation_name.strip()
        if not die_number or not operation_code:
            raise ValueError("Gesenknummer und AG-Code sind Pflichtfelder.")
        operation_name = operation_name or operation_code
        if seconds_per_piece <= 0:
            raise ValueError("Die Vorgabezeit muss größer als null sein.")
        now = self._now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO dies(die_number, description, note, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(die_number) DO UPDATE SET
                    description = excluded.description,
                    note = excluded.note,
                    active = 1,
                    updated_at = excluded.updated_at
                """,
                (die_number, die_description.strip(), die_note.strip(), now, now),
            )
            connection.execute(
                """
                INSERT INTO operations(code, name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    active = 1,
                    updated_at = excluded.updated_at
                """,
                (operation_code, operation_name, now, now),
            )
            die_id = int(connection.execute(
                "SELECT id FROM dies WHERE die_number = ?", (die_number,)
            ).fetchone()["id"])
            operation_id = int(connection.execute(
                "SELECT id FROM operations WHERE code = ?", (operation_code,)
            ).fetchone()["id"])
            connection.execute(
                """
                INSERT INTO standards(
                    die_id, operation_id, seconds_per_piece, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(die_id, operation_id) DO UPDATE SET
                    seconds_per_piece = excluded.seconds_per_piece,
                    active = 1,
                    updated_at = excluded.updated_at
                """,
                (die_id, operation_id, seconds_per_piece, now, now),
            )
            return int(connection.execute(
                "SELECT id FROM standards WHERE die_id = ? AND operation_id = ?",
                (die_id, operation_id),
            ).fetchone()["id"])

    def list_catalog(self, *, search: str = "", include_inactive: bool = False) -> list[dict[str, Any]]:
        conditions = [] if include_inactive else ["s.active = 1", "d.active = 1", "op.active = 1"]
        parameters: list[Any] = []
        if search.strip():
            term = f"%{search.strip()}%"
            conditions.append(
                "(d.die_number LIKE ? OR d.description LIKE ? OR op.code LIKE ? OR op.name LIKE ?)"
            )
            parameters.extend([term] * 4)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT s.id, d.die_number, d.description, d.note AS die_note,
                       op.code AS operation_code, op.name AS operation_name,
                       s.seconds_per_piece, s.active
                FROM standards s
                JOIN dies d ON d.id = s.die_id
                JOIN operations op ON op.id = s.operation_id
                {where}
                ORDER BY d.die_number, op.code
                """,  # noqa: S608 -- where contains only fixed fragments
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def standards_for_die(self, die_number: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT s.id, op.code AS operation_code, op.name AS operation_name,
                       s.seconds_per_piece
                FROM standards s
                JOIN dies d ON d.id = s.die_id
                JOIN operations op ON op.id = s.operation_id
                WHERE d.die_number = ? AND d.active = 1 AND op.active = 1 AND s.active = 1
                ORDER BY op.code
                """,
                (die_number.strip(),),
            ).fetchall()
        return [dict(row) for row in rows]

    def deactivate_standard(self, standard_id: int) -> None:
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE standards SET active = 0, updated_at = ? WHERE id = ?",
                (self._now(), standard_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Vorgabe nicht gefunden.")
