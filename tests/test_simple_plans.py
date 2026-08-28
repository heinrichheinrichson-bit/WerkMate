from pathlib import Path

import pytest

from werkmate.simple_plans import SimplePlanStore


def sample(name: str = "Frühschicht") -> dict:
    return {
        "name": name,
        "shift_number": 1,
        "start": "05:45",
        "jobs": [{"die": "8720", "quantity": 12, "seconds_per_piece": 1200}],
    }


def test_simple_plan_store_saves_loads_duplicates_and_deletes(tmp_path: Path) -> None:
    store = SimplePlanStore(tmp_path / "plans.json")
    store.save(sample())
    assert store.list()[0]["jobs"][0]["die"] == "8720"

    store.duplicate("Frühschicht", "Frühschicht Kopie")
    assert [item["name"] for item in store.list()] == ["Frühschicht", "Frühschicht Kopie"]

    store.delete("Frühschicht")
    assert [item["name"] for item in store.list()] == ["Frühschicht Kopie"]


def test_simple_plan_store_rejects_duplicate_name(tmp_path: Path) -> None:
    store = SimplePlanStore(tmp_path / "plans.json")
    store.save(sample())
    with pytest.raises(ValueError, match="bereits"):
        store.save(sample())
