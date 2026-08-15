import json
from pathlib import Path

import pytest

from scripts.evaluate_model import (
    calculate_metrics,
    evaluate,
    evaluate_ridge,
    format_summary,
)


ROOT = Path(__file__).resolve().parent.parent


def load_records():
    with (
        ROOT / "data" / "seed_28days.json"
    ).open(encoding="utf-8") as file:
        return json.load(file)["records"]


def test_calculate_metrics():
    result = calculate_metrics(
        actual=[10, 20],
        predicted=[12, 16],
    )

    assert result == {
        "mae": 3.0,
        "rmse": 3.162,
    }


def test_walk_forward_uses_fourteen_test_days():
    result = evaluate_ridge(load_records())

    assert result["method"] == "walk-forward"
    assert result["initialTrainDays"] == 14
    assert result["testDays"] == 14
    assert len(result["predictions"]) == 14
    assert result["predictions"][0][
        "recordedAt"
    ] == "2026-08-01"
    assert result["predictions"][-1][
        "recordedAt"
    ] == "2026-08-14"
    assert result["ridge"] == {
        "mae": 4.529,
        "rmse": 5.653,
        "directionAccuracy": 0.643,
        "rangeCoverage": 0.5,
    }
    assert result["baselines"] == {
        "historicalMean": {
            "mae": 9.981,
            "rmse": 12.972,
        },
        "previousScore": {
            "mae": 7.214,
            "rmse": 10.899,
        },
    }


def test_evaluation_reports_known_pattern_truth():
    result = evaluate(load_records())
    pattern = result["habitPattern"]

    assert pattern["top3OrderMatch"] is True
    assert pattern["lagMatches"] == 3
    assert pattern["lagChecks"] == 3
    assert (
        pattern["controlImpactsBelowPointOne"]
        is True
    )


def test_evaluation_rejects_too_few_records():
    with pytest.raises(ValueError):
        evaluate_ridge(load_records()[:14])


def test_summary_contains_core_metrics_only():
    summary = format_summary(evaluate(load_records()))

    assert "MAE: 4.529" in summary
    assert "RMSE: 5.653" in summary
    assert "방향 정확도: 64.3%" in summary
    assert "범위 포함률: 50.0%" in summary
    assert "recordedAt" not in summary
