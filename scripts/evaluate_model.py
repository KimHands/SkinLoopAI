import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

sys.path.insert(0, str(ROOT))

from src.habit_pattern import analyze_patterns
from src.validation import validate_records
from src.whatif import (
    build_model,
    prepare_training_data,
    score_range,
)


DEFAULT_INPUT = ROOT / "data" / "seed_28days.json"
MIN_TRAIN_RECORDS = 14


def classify_direction(value, previous):
    difference = value - previous

    if difference >= 1:
        return "improve"
    if difference <= -1:
        return "worsen"
    return "unclear"


def calculate_metrics(
    actual,
    predicted,
):
    errors = np.asarray(actual) - np.asarray(predicted)

    return {
        "mae": round(
            float(np.mean(np.abs(errors))),
            3,
        ),
        "rmse": round(
            math.sqrt(float(np.mean(errors ** 2))),
            3,
        ),
    }


def evaluate_ridge(
    records,
    min_train_records=MIN_TRAIN_RECORDS,
):
    validate_records(records)

    if len(records) <= min_train_records:
        raise ValueError(
            "성능평가에는 학습 구간 이후 "
            "최소 1일이 더 필요합니다."
        )

    features, target = prepare_training_data(records)
    first_test_index = min_train_records - 1

    actual_values = []
    ridge_values = []
    mean_values = []
    previous_values = []
    direction_matches = 0
    covered = 0
    predictions = []

    for test_index in range(
        first_test_index,
        len(features),
    ):
        train_features = features.iloc[:test_index]
        train_target = target.iloc[:test_index]
        test_features = features.iloc[
            [test_index]
        ]

        model = build_model()
        model.fit(train_features, train_target)

        predicted = float(
            model.predict(test_features)[0]
        )
        actual = float(target.iloc[test_index])
        historical_mean = float(
            train_target.mean()
        )
        previous_score = float(
            records[test_index]["skin_score"]
        )

        train_predictions = model.predict(
            train_features
        )
        error = max(
            2.0,
            float(
                np.std(
                    train_target - train_predictions,
                    ddof=1,
                )
            ),
        )
        predicted_range = score_range(
            predicted,
            error,
        )

        actual_direction = classify_direction(
            actual,
            previous_score,
        )
        predicted_direction = classify_direction(
            predicted,
            previous_score,
        )

        direction_matches += int(
            actual_direction == predicted_direction
        )
        covered += int(
            predicted_range["min"]
            <= actual
            <= predicted_range["max"]
        )

        actual_values.append(actual)
        ridge_values.append(predicted)
        mean_values.append(historical_mean)
        previous_values.append(previous_score)

        predictions.append({
            "recordedAt": records[
                test_index + 1
            ]["recorded_at"],
            "actual": round(actual, 1),
            "predicted": round(predicted, 1),
            "range": predicted_range,
            "actualDirection": actual_direction,
            "predictedDirection": predicted_direction,
        })

    test_count = len(actual_values)
    ridge_metrics = calculate_metrics(
        actual_values,
        ridge_values,
    )
    ridge_metrics.update({
        "directionAccuracy": round(
            direction_matches / test_count,
            3,
        ),
        "rangeCoverage": round(
            covered / test_count,
            3,
        ),
    })

    return {
        "method": "walk-forward",
        "recordDays": len(records),
        "initialTrainDays": min_train_records,
        "testDays": test_count,
        "ridge": ridge_metrics,
        "baselines": {
            "historicalMean": calculate_metrics(
                actual_values,
                mean_values,
            ),
            "previousScore": calculate_metrics(
                actual_values,
                previous_values,
            ),
        },
        "predictions": predictions,
    }


def evaluate_habit_pattern(records):
    result = analyze_patterns(records)
    expected = [
        ("sleep_short", 1),
        ("late_snack", 1),
        ("stress", 0),
    ]
    actual = [
        (item["factor"], item["lag"])
        for item in result["impacts"]
    ]
    impact_map = {
        item["factor"]: item["impact"]
        for item in result["allImpacts"]
    }

    return {
        "expectedTop3": [
            factor for factor, _ in expected
        ],
        "actualTop3": [
            factor for factor, _ in actual
        ],
        "top3OrderMatch": (
            [factor for factor, _ in actual]
            == [factor for factor, _ in expected]
        ),
        "lagMatches": sum(
            actual_item == expected_item
            for actual_item, expected_item in zip(
                actual,
                expected,
            )
        ),
        "lagChecks": len(expected),
        "controlImpactsBelowPointOne": (
            impact_map["exercise"] < 0.1
            and impact_map["cosmetic_changed"] < 0.1
        ),
    }


def evaluate(records):
    return {
        "evaluationType": (
            "synthetic-internal-validation"
        ),
        "habitPattern": evaluate_habit_pattern(
            records
        ),
        "ridgeWhatIf": evaluate_ridge(records),
        "limitations": [
            "28일 합성 샘플 1개에 대한 내부 검증",
            "실제 사용자 데이터의 일반화 성능이 아님",
            "estimatedDifference의 인과 효과 검증이 아님",
        ],
    }


def load_records(path):
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)["records"]


def format_summary(result):
    pattern = result["habitPattern"]
    evaluation = result["ridgeWhatIf"]
    ridge = evaluation["ridge"]
    baselines = evaluation["baselines"]

    return "\n".join([
        "[28일 합성 데이터 내부 성능평가]",
        f"평가 방법: {evaluation['method']}",
        f"평가 일수: {evaluation['testDays']}일",
        "",
        "[Ridge]",
        f"MAE: {ridge['mae']}",
        f"RMSE: {ridge['rmse']}",
        (
            "방향 정확도: "
            f"{ridge['directionAccuracy'] * 100:.1f}%"
        ),
        (
            "범위 포함률: "
            f"{ridge['rangeCoverage'] * 100:.1f}%"
        ),
        "",
        "[기준 모델 비교]",
        (
            "과거 평균 - "
            f"MAE {baselines['historicalMean']['mae']}, "
            f"RMSE {baselines['historicalMean']['rmse']}"
        ),
        (
            "직전 점수 - "
            f"MAE {baselines['previousScore']['mae']}, "
            f"RMSE {baselines['previousScore']['rmse']}"
        ),
        "",
        "[HabitPattern]",
        (
            "상위 3개 순서 일치: "
            f"{pattern['top3OrderMatch']}"
        ),
        (
            "lag 일치: "
            f"{pattern['lagMatches']}/{pattern['lagChecks']}"
        ),
        (
            "대조군 impact 0.1 미만: "
            f"{pattern['controlImpactsBelowPointOne']}"
        ),
        "",
        "※ 합성 샘플 1개에 대한 내부 검증이며, "
        "실사용 일반화 성능이나 인과 효과가 아닙니다.",
    ])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="SkinLoop 합성 데이터 내부 성능평가",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="평가할 시드 JSON 경로",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="날짜별 예측을 포함한 전체 JSON 출력",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    result = evaluate(load_records(args.input))
    if args.details:
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(format_summary(result))


if __name__ == "__main__":
    main()
