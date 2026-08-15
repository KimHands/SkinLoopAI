import json
from copy import deepcopy
from pathlib import Path

import pytest

from src.habit_pattern import analyze_patterns


ROOT = Path(__file__).resolve().parent.parent


def load_records():
    with (
        ROOT / "data" / "seed_28days.json"
    ).open(encoding="utf-8") as file:
        return json.load(file)["records"]


def test_sample_pattern_result_is_unchanged():
    result = analyze_patterns(load_records())

    assert result == {
        "recordDays": 28,
        "confidence": "high",
        "impacts": [
            {
                "factor": "sleep_short",
                "label": "6시간 미만 수면",
                "lag": 1,
                "corr": -0.755,
                "impact": 0.417,
            },
            {
                "factor": "late_snack",
                "label": "야식",
                "lag": 1,
                "corr": -0.699,
                "impact": 0.357,
            },
            {
                "factor": "stress",
                "label": "스트레스",
                "lag": 0,
                "corr": -0.468,
                "impact": 0.16,
            },
        ],
        "allImpacts": [
            {
                "factor": "sleep_short",
                "label": "6시간 미만 수면",
                "lag": 1,
                "corr": -0.755,
                "impact": 0.417,
            },
            {
                "factor": "late_snack",
                "label": "야식",
                "lag": 1,
                "corr": -0.699,
                "impact": 0.357,
            },
            {
                "factor": "stress",
                "label": "스트레스",
                "lag": 0,
                "corr": -0.468,
                "impact": 0.16,
            },
            {
                "factor": "exercise",
                "label": "운동 시간",
                "lag": 3,
                "corr": 0.22,
                "impact": 0.035,
            },
            {
                "factor": "cosmetic_changed",
                "label": "화장품 변경",
                "lag": 2,
                "corr": -0.207,
                "impact": 0.031,
            },
        ],
        "evidenceDates": [
            "2026-07-29",
            "2026-08-01",
            "2026-08-03",
        ],
        "modelVersion": (
            "habitpattern-spearman-v1.0"
        ),
    }


def test_pattern_returns_need_more_for_six_days():
    result = analyze_patterns(load_records()[:6])

    assert result == {
        "recordDays": 6,
        "confidence": None,
        "impacts": [],
        "allImpacts": [],
        "evidenceDates": [],
        "reason": "NOT_ENOUGH_RECORDS",
        "needMore": 1,
    }


def test_pattern_rejects_missing_field():
    records = deepcopy(load_records())
    del records[0]["sleep_hours"]

    with pytest.raises(ValueError):
        analyze_patterns(records)


def test_pattern_rejects_duplicate_date():
    records = deepcopy(load_records())
    records[1]["recorded_at"] = (
        records[0]["recorded_at"]
    )

    with pytest.raises(ValueError):
        analyze_patterns(records)
