import json
from pathlib import Path

import pytest

from src.whatif import run_whatif


ROOT = Path(__file__).resolve().parent.parent


def load_records():
    with (
        ROOT / "data" / "seed_28days.json"
    ).open(encoding="utf-8") as file:
        return json.load(file)["records"]


def test_sample_whatif_result_is_unchanged():
    result = run_whatif(
        records=load_records(),
        target_habit="sleep_short",
        change_value=1.0,
    )

    assert result == {
        "targetHabit": "sleep_short",
        "label": "수면 +1시간",
        "current": {
            "range": {
                "min": 61,
                "max": 69,
            },
            "trend": [65, 65, 65, 65],
        },
        "changed": {
            "range": {
                "min": 69,
                "max": 77,
            },
            "trend": [67, 69, 71, 73],
        },
        "direction": "improve",
        "confidence": "high",
        "estimatedDifference": 7.2,
        "modelVersion": "whatif-ridge-v1.0",
    }


def test_whatif_returns_need_more_for_thirteen_days():
    result = run_whatif(
        records=load_records()[:13],
        target_habit="sleep_short",
        change_value=1.0,
    )

    assert result == {
        "targetHabit": "sleep_short",
        "confidence": None,
        "reason": "NOT_ENOUGH_RECORDS",
        "needMore": 1,
    }


@pytest.mark.parametrize(
    ("target_habit", "change_value"),
    [
        ("unknown", 1),
        ("sleep_short", 0),
        ("sleep_short", -1),
        ("late_snack", 8),
        ("stress", 5),
        ("exercise", 301),
    ],
)
def test_whatif_rejects_invalid_scenario(
    target_habit,
    change_value,
):
    with pytest.raises(ValueError):
        run_whatif(
            records=load_records(),
            target_habit=target_habit,
            change_value=change_value,
        )


@pytest.mark.parametrize(
    ("target_habit", "change_value"),
    [
        ("sleep_short", 1),
        ("late_snack", 1),
        ("stress", 1),
        ("exercise", 10),
    ],
)
def test_whatif_supports_all_defined_habits(
    target_habit,
    change_value,
):
    result = run_whatif(
        records=load_records(),
        target_habit=target_habit,
        change_value=change_value,
    )

    assert result["targetHabit"] == target_habit
    assert len(result["current"]["trend"]) == 4
    assert len(result["changed"]["trend"]) == 4
