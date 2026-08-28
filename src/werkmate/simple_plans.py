"""Kleiner lokaler JSON-Speicher für den einfachen Schichtrechner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SimplePlanStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def list(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    def save(self, plan: dict[str, Any], *, replace_name: str | None = None) -> None:
        plans = self.list()
        name = str(plan["name"]).strip()
        if not name:
            raise ValueError("Bitte einen Namen für den Plan eingeben.")
        duplicate = next(
            (item for item in plans if item.get("name") == name and item.get("name") != replace_name),
            None,
        )
        if duplicate:
            raise ValueError("Ein Plan mit diesem Namen ist bereits gespeichert.")
        if replace_name:
            plans = [item for item in plans if item.get("name") != replace_name]
        plans.append({**plan, "name": name})
        plans.sort(key=lambda item: str(item.get("name", "")).casefold())
        self._write(plans)

    def delete(self, name: str) -> None:
        self._write([item for item in self.list() if item.get("name") != name])

    def duplicate(self, name: str, new_name: str) -> None:
        source = next((item for item in self.list() if item.get("name") == name), None)
        if source is None:
            raise ValueError("Der ausgewählte Plan wurde nicht gefunden.")
        self.save({**source, "name": new_name})

    def _write(self, plans: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(plans, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.path)
