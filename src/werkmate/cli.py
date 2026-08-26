"""Bedienbarer lokaler WerkMate-MVP für die Konsole."""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from . import __version__
from .database import WerkMateDatabase
from .service import WerkMateService
from .timecalc import minutes_to_seconds, seconds_to_minutes


def default_database_path() -> Path:
    configured = os.environ.get("WERKMATE_DB")
    if configured:
        return Path(configured)
    root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "WerkMate"
    return root / "werkmate.sqlite3"


def parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace(" ", "T")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Zeitformat: JJJJ-MM-TT HH:MM, z. B. 2026-08-26 13:45"
        ) from error


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(abs(seconds), 3_600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="werkmate", description="Lokaler Auftrags- und Vorgabezeiten-Assistent"
    )
    parser.add_argument("--version", action="version", version=f"WerkMate {__version__}")
    parser.add_argument("--db", type=Path, default=default_database_path())
    commands = parser.add_subparsers(dest="command", required=True)

    new = commands.add_parser("auftrag-neu", help="Neuen Auftrag anlegen")
    new.add_argument("--nummer", required=True)
    new.add_argument("--gesenk", required=True)
    new.add_argument("--arbeitsgang", required=True)
    new.add_argument("--menge", type=int, required=True)
    new.add_argument("--minuten", required=True, help="Vorgabezeit je Stück, z. B. 7,5")
    new.add_argument("--notiz", default="")

    commands.add_parser("auftraege", help="Aufträge und offene Mengen anzeigen")

    start = commands.add_parser("start", help="Persönlichen Arbeitseinsatz starten")
    start.add_argument("--auftrag", type=int, required=True, help="Interne Auftrags-ID")
    start.add_argument("--menge", type=int, required=True)
    start.add_argument("--anmeldung", type=parse_datetime, required=True)
    start.add_argument("--schicht", type=int, choices=(1, 2, 3))
    start.add_argument("--schichtende", type=parse_datetime)
    start.add_argument("--notiz", default="")

    status = commands.add_parser("status", help="Laufenden Einsatz anzeigen")
    status.add_argument("--jetzt", type=parse_datetime, help="Test-/Korrekturzeit")

    finish = commands.add_parser("rueckmelden", help="Teil- oder Abschlussmeldung speichern")
    finish.add_argument("--einsatz", type=int, required=True)
    finish.add_argument("--stueck", type=int, required=True)
    finish.add_argument("--abmeldung", type=parse_datetime, required=True)
    finish.add_argument("--notiz", default="")
    finish.add_argument(
        "--bestaetigen", action="store_true",
        help="Erforderlich, wenn die Abmeldezeit deutlich vom Soll abweicht",
    )

    history = commands.add_parser("historie", help="Persönliche Meldungen anzeigen")
    history.add_argument("--limit", type=int, default=30)

    handoff = commands.add_parser("abgeben", help="Restauftrag nicht weiterverfolgen")
    handoff.add_argument("--auftrag", type=int, required=True)
    handoff.add_argument("--grund", default="")
    return parser


def warn_unusual_end(session: dict, reported_end: datetime) -> str | None:
    start = datetime.fromisoformat(session["reported_started_at"])
    target = datetime.fromisoformat(session["target_end"])
    if reported_end < start:
        return "Die Abmeldezeit liegt vor der Anmeldezeit."
    deviation = abs((reported_end - target).total_seconds())
    if deviation > 30 * 60:
        return "Die Abmeldezeit weicht mehr als 30 Minuten vom Soll-Ende ab."
    return None


def run(args: argparse.Namespace) -> int:
    database = WerkMateDatabase(args.db)
    service = WerkMateService(database)

    if args.command == "auftrag-neu":
        order_id = service.create_order(
            order_number=args.nummer,
            die_number=args.gesenk,
            operation=args.arbeitsgang,
            original_quantity=args.menge,
            seconds_per_piece=minutes_to_seconds(args.minuten),
            note=args.notiz,
        )
        print(f"Auftrag angelegt · ID {order_id} · {args.menge} Stück")
        return 0

    if args.command == "auftraege":
        orders = database.list_orders()
        if not orders:
            print("Noch keine Aufträge gespeichert.")
        for order in orders:
            print(
                f"#{order['id']} · {order['order_number']} · Ges. {order['die_number']} · "
                f"{order['operation']} · offen {order['open_quantity']}/{order['original_quantity']} · "
                f"{seconds_to_minutes(order['seconds_per_piece'])} min/Stück · {order['status']}"
            )
        return 0

    if args.command == "start":
        session_id = service.start_work(
            order_id=args.auftrag,
            quantity=args.menge,
            reported_start=args.anmeldung,
            shift_number=args.schicht,
            custom_shift_end=args.schichtende,
            note=args.notiz,
        )
        session = database.get_session(session_id)
        print(f"Einsatz #{session_id} gestartet · Soll-Ende {session['target_end'][0:16].replace('T', ' ')}")
        if session["pause_seconds"]:
            print(f"Verrechnete Pause: +{session['pause_seconds'] // 60} Minuten")
        return 0

    if args.command == "status":
        status = service.status(args.jetzt)
        if status is None:
            print("Kein laufender Arbeitseinsatz.")
            return 0
        sign = "+" if status["time_state"] == "ueberzogen" else ""
        print(f"{status['order_number']} · Ges. {status['die_number']} · {status['operation']}")
        print(f"{status['time_state'].upper()}: {sign}{format_duration(status['time_seconds'])}")
        print(f"Soll-Ende: {status['target_end'][0:16].replace('T', ' ')}")
        if "pieces_until_shift_end" in status:
            print(f"Bis Schichtende laut Vorgabe: {status['pieces_until_shift_end']} vollständige Stück")
            print(
                "Nächstes Stück würde "
                f"+{format_duration(status['next_piece_overtime_seconds'])} Überzeit benötigen"
            )
        return 0

    if args.command == "rueckmelden":
        session = database.get_session(args.einsatz)
        if session is None:
            raise ValueError("Arbeitseinsatz nicht gefunden.")
        warning = warn_unusual_end(session, args.abmeldung)
        if warning and not args.bestaetigen:
            print(f"WARNUNG: {warning}")
            print("Erneut mit --bestaetigen ausführen, um die Zeit bewusst zu übernehmen.")
            return 2
        service.finish_work(
            args.einsatz,
            completed_quantity=args.stueck,
            reported_end=args.abmeldung,
            note=args.notiz,
        )
        order = database.get_order(session["order_id"])
        print(f"Rückmeldung gespeichert · {args.stueck} Stück · offen {order['open_quantity']} Stück")
        return 0

    if args.command == "historie":
        entries = database.history(limit=args.limit)
        if not entries:
            print("Noch keine persönlichen Meldungen gespeichert.")
        for item in entries:
            ended = item["reported_ended_at"] or "noch laufend"
            quantity = item["completed_quantity"] if item["completed_quantity"] is not None else "–"
            print(
                f"Einsatz #{item['id']} · {item['order_number']} · {item['die_number']}/{item['operation']} · "
                f"{item['reported_started_at'][0:16].replace('T', ' ')} → "
                f"{str(ended)[0:16].replace('T', ' ')} · {quantity} Stück · {item['status']}"
            )
            if item["note"]:
                print(f"  Notiz: {item['note']}")
        return 0

    if args.command == "abgeben":
        database.hand_off_order(args.auftrag, reason=args.grund)
        print("Restauftrag als abgegeben/nicht weiterverfolgt markiert.")
        return 0

    return 1


def main() -> None:
    parser = build_parser()
    try:
        raise SystemExit(run(parser.parse_args()))
    except (ValueError, OSError) as error:
        parser.exit(2, f"Fehler: {error}\n")


if __name__ == "__main__":
    main()

