"""Nachvollziehbare Soll-/Ist-Auswertung persönlicher Arbeitseinsätze."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PerformanceResult:
    time_delta_seconds: int
    time_delta_percent: float
    quantity_delta: int
    quantity_delta_percent: float


def calculate_performance(session: dict) -> PerformanceResult | None:
    """Vergleicht gemeldetes Ende/Stück mit der Planung des Einsatzes."""
    if session.get("status") in ("laufend", "sollzeit_erreicht", "ueberzogen", "abgebrochen"):
        return None
    if session.get("reported_ended_at") is None or session.get("completed_quantity") is None:
        return None
    planned_quantity = int(session["quantity_to_process"])
    seconds_per_piece = int(session["seconds_per_piece"])
    if planned_quantity <= 0 or seconds_per_piece <= 0:
        return None
    reported_end = datetime.fromisoformat(str(session["reported_ended_at"]))
    planned_end = datetime.fromisoformat(str(session["target_end"]))
    time_delta = int((reported_end - planned_end).total_seconds())
    planned_seconds = int(session.get("planned_seconds") or planned_quantity * seconds_per_piece)
    measured_quantity = (
        session.get("reported_quantity")
        if session.get("session_kind") == "credit"
        else session.get("completed_quantity")
    )
    if measured_quantity is None:
        return None
    quantity_delta = int(measured_quantity) - planned_quantity
    return PerformanceResult(
        time_delta_seconds=time_delta,
        time_delta_percent=time_delta / planned_seconds * 100,
        quantity_delta=quantity_delta,
        quantity_delta_percent=quantity_delta / planned_quantity * 100,
    )


def format_time_performance(result: PerformanceResult | None) -> str:
    if result is None:
        return "–"
    minutes = f"{abs(result.time_delta_seconds) / 60:.1f}".replace(".", ",")
    percent = f"{abs(result.time_delta_percent):.1f}".replace(".", ",")
    if result.time_delta_seconds > 0:
        return f"🔴 {minutes} min Verzug (+{percent} %)"
    if result.time_delta_seconds < 0:
        return f"🟢 {minutes} min früher ({percent} %)"
    return "⚪ genau nach Plan (0,0 %)"


def format_quantity_performance(result: PerformanceResult | None) -> str:
    if result is None:
        return "–"
    percent = f"{abs(result.quantity_delta_percent):.1f}".replace(".", ",")
    if result.quantity_delta > 0:
        return f"🟢 +{result.quantity_delta} Stück (+{percent} %)"
    if result.quantity_delta < 0:
        return f"🔴 {result.quantity_delta} Stück (-{percent} %)"
    return "⚪ genau nach Plan (0,0 %)"
