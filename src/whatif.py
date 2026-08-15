import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.habit_pattern import get_confidence
from src.validation import (
    validate_records,
    validate_whatif_request,
)


def prepare_training_data(records):
    df = (
        pd.DataFrame(records)
        .sort_values("recorded_at")
        .reset_index(drop=True)
    )

    df["late_snack"] = (
        df["late_snack"].astype(int)
    )

    df["cosmetic_changed"] = (
        df["cosmetic_changed"].astype(int)
    )

    # 오늘 피부 점수를 예측할 때
    # 전날 수면과 전날 야식을 사용한다.
    features = pd.DataFrame({
        "sleep_hours": (
            df["sleep_hours"].shift(1)
        ),
        "late_snack": (
            df["late_snack"].shift(1)
        ),
        "stress_level": (
            df["stress_level"]
        ),
        "exercise_min": (
            df["exercise_min"]
        ),
        "cosmetic_changed": (
            df["cosmetic_changed"]
        ),
    })

    target = df["skin_score"]

    # 첫날은 전날 기록이 없어 제외
    valid = features.notna().all(axis=1)

    return (
        features[valid].reset_index(
            drop=True
        ),
        target[valid].reset_index(
            drop=True
        ),
    )


def apply_scenario(
    features,
    target_habit,
    change_value,
):
    changed = features.copy()

    if target_habit == "sleep_short":
        changed["sleep_hours"] = (
            changed["sleep_hours"]
            + change_value
        ).clip(
            0,
            14,
        )

        label = (
            f"수면 +{change_value:g}시간"
        )

    elif target_habit == "late_snack":
        # change_value는 주당 감소 횟수
        changed["late_snack"] = (
            changed["late_snack"]
            - change_value / 7
        ).clip(
            0,
            1,
        )

        label = (
            f"야식 주 {change_value:g}회 줄이기"
        )

    elif target_habit == "stress":
        changed["stress_level"] = (
            changed["stress_level"]
            - change_value
        ).clip(
            1,
            5,
        )

        label = (
            f"스트레스 "
            f"{change_value:g}단계 낮추기"
        )

    else:
        changed["exercise_min"] = (
            changed["exercise_min"]
            + change_value
        ).clip(
            0,
            300,
        )

        label = (
            f"운동 +{change_value:g}분"
        )

    return changed, label


def score_range(mean, error):
    return {
        "min": max(
            20,
            round(mean - error),
        ),
        "max": min(
            100,
            round(mean + error),
        ),
    }


def build_model():
    return make_pipeline(
        StandardScaler(),
        Ridge(alpha=3.0),
    )


def run_whatif(
    records,
    target_habit,
    change_value,
):
    validate_records(records)

    record_days = len(records)

    if record_days < 14:
        return {
            "targetHabit": target_habit,
            "confidence": None,
            "reason": (
                "NOT_ENOUGH_RECORDS"
            ),
            "needMore": (
                14 - record_days
            ),
        }

    validate_whatif_request(
        target_habit,
        change_value,
    )

    features, target = (
        prepare_training_data(records)
    )

    # 적은 데이터에서도 비교적 안정적인
    # Ridge 회귀 사용
    model = build_model()

    model.fit(
        features,
        target,
    )

    changed_features, label = (
        apply_scenario(
            features,
            target_habit,
            change_value,
        )
    )

    current_predictions = (
        model.predict(features)
    )

    changed_predictions = (
        model.predict(changed_features)
    )

    current_mean = float(
        np.mean(current_predictions)
    )

    changed_mean = float(
        np.mean(changed_predictions)
    )

    difference = (
        changed_mean - current_mean
    )

    # 실제값과 현재 예측값 차이를
    # 점수 범위 계산에 사용
    error = max(
        2.0,
        float(
            np.std(
                target
                - current_predictions,
                ddof=1,
            )
        ),
    )

    if difference >= 1:
        direction = "improve"

    elif difference <= -1:
        direction = "worsen"

    else:
        direction = "unclear"

    # 4주 그래프용 값
    current_trend = [
        round(current_mean)
    ] * 4

    changed_trend = [
        round(
            current_mean
            + difference * week / 4
        )
        for week in range(1, 5)
    ]

    return {
        "targetHabit": target_habit,
        "label": label,
        "current": {
            "range": score_range(
                current_mean,
                error,
            ),
            "trend": current_trend,
        },
        "changed": {
            "range": score_range(
                changed_mean,
                error,
            ),
            "trend": changed_trend,
        },
        "direction": direction,
        "confidence": get_confidence(
            record_days
        ),
        "estimatedDifference": round(
            difference,
            1,
        ),
        "modelVersion": (
            "whatif-ridge-v1.0"
        ),
    }
