"""Lokale SQLite-Persistenz für Aufträge, Arbeitseinsätze und Korrekturen."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 2


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
                    note TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'laufend',
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

                CREATE INDEX IF NOT EXISTS idx_sessions_order ON work_sessions(order_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_reported_start
                    ON work_sessions(reported_started_at);
                CREATE INDEX IF NOT EXISTS idx_corrections_entity
                    ON correction_log(entity_type, entity_id);
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
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
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
    ) -> int:
        now = self._now()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO orders(
                    order_number, die_number, operation, original_quantity,
                    seconds_per_piece, note, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_number.strip(), die_number.strip(), operation.strip(),
                    original_quantity, seconds_per_piece, note.strip(), now, now,
                ),
            )
            return int(cursor.lastrowid)

    def get_order(self, order_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT o.*,
                       COALESCE(SUM(ws.completed_quantity), 0) AS completed_quantity,
                       o.original_quantity - COALESCE(SUM(ws.completed_quantity), 0)
                           AS open_quantity
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

    def list_orders(self, *, include_handed_off: bool = True) -> list[dict[str, Any]]:
        clause = "" if include_handed_off else "WHERE status != 'abgegeben'"
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
    ) -> int:
        order = self.get_order(order_id)
        if order is None:
            raise ValueError("Auftrag nicht gefunden.")
        if quantity_to_process <= 0 or quantity_to_process > order["open_quantity"]:
            raise ValueError("Die Einsatzmenge überschreitet die offene Auftragsmenge.")
        if self.active_session() is not None:
            raise ValueError("Es läuft bereits ein persönlicher Arbeitseinsatz.")
        now = self._now()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO work_sessions(
                    order_id, shift_name, shift_start, shift_end,
                    quantity_to_process, seconds_per_piece,
                    actual_started_at, reported_started_at, target_end,
                    pause_seconds, note, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id, shift_name,
                    shift_start.isoformat() if shift_start else None,
                    shift_end.isoformat() if shift_end else None,
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
        actual_confirmed_at: datetime,
        reported_ended_at: datetime,
        note: str = "",
    ) -> None:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("Arbeitseinsatz nicht gefunden.")
        if completed_quantity < 0 or completed_quantity > session["quantity_to_process"]:
            raise ValueError("Die fertiggemeldete Menge ist ungültig.")
        order = self.get_order(int(session["order_id"]))
        if order is None or completed_quantity > order["open_quantity"]:
            raise ValueError("Die Rückmeldung überschreitet die offene Auftragsmenge.")

        now = self._now()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE work_sessions
                SET completed_quantity = ?, actual_confirmed_at = ?,
                    reported_ended_at = ?, note = ?, status = 'abgeschlossen',
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    completed_quantity, actual_confirmed_at.isoformat(),
                    reported_ended_at.isoformat(), note.strip(), now, session_id,
                ),
            )
            totals = connection.execute(
                """
                SELECT o.original_quantity,
                       COALESCE(SUM(ws.completed_quantity), 0) AS completed
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
                "reported_started_at", "reported_ended_at", "completed_quantity", "note"
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

    def update_order(
        self,
        order_id: int,
        *,
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

        changes = {
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
