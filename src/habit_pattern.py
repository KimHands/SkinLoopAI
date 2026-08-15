import math

import pandas as pd
from scipy.stats import spearmanr

from src.validation import validate_records


FACTOR_CONFIG = {
    "sleep_short": {
        "column": "sleep_short",
        "label": "6시간 미만 수면",
    },
    "late_snack": {
        "column": "late_snack",
        "label": "야식",
    },
    "stress": {
        "column": "stress_level",
        "label": "스트레스",
    },
    "exercise": {
        "column": "exercise_min",
        "label": "운동 시간",
    },
    "cosmetic_changed": {
        "column": "cosmetic_changed",
        "label": "화장품 변경",
    },
}


def get_confidence(record_days):
    if record_days < 7:
        return None
    if record_days < 14:
        return "low"
    if record_days < 21:
        return "medium"
    return "high"


def prepare_dataframe(records):
    df = pd.DataFrame(records).copy()

    required = {
        "recorded_at",
        "sleep_hours",
        "late_snack",
        "stress_level",
        "exercise_min",
        "cosmetic_changed",
        "skin_score",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"필수 필드가 없습니다: {sorted(missing)}"
        )

    df = (
        df.sort_values("recorded_at")
        .reset_index(drop=True)
    )

    # 수면시간이 6시간 미만이면 1
    df["sleep_short"] = (
        df["sleep_hours"] < 6
    ).astype(int)

    # boolean 값을 상관분석용 0과 1로 변환
    df["late_snack"] = (
        df["late_snack"].astype(int)
    )

    df["cosmetic_changed"] = (
        df["cosmetic_changed"].astype(int)
    )

    return df


def best_lag_correlation(df, column, lags):
    best = {
        "lag": 0,
        "corr": 0.0,
    }

    for lag in lags:
        shifted = df[column].shift(lag)

        valid = pd.DataFrame({
            "factor": shifted,
            "skin": df["skin_score"],
        }).dropna()

        if (
            valid["factor"].nunique() < 2
            or valid["skin"].nunique() < 2
        ):
            corr = 0.0
        else:
            corr, _ = spearmanr(
                valid["factor"],
                valid["skin"],
            )

            corr = (
                0.0
                if math.isnan(corr)
                else float(corr)
            )

        if abs(corr) > abs(best["corr"]):
            best = {
                "lag": lag,
                "corr": corr,
            }

    return best


def find_evidence_dates(
    df,
    factor,
    lag,
    limit=3,
):
    column = FACTOR_CONFIG[factor]["column"]
    shifted = df[column].shift(lag)
    median_score = df["skin_score"].median()

    if factor in {
        "sleep_short",
        "late_snack",
        "cosmetic_changed",
    }:
        risky = shifted == 1

    elif factor == "stress":
        risky = shifted >= 4

    else:
        # 운동시간이 10분 이하인 날
        risky = shifted <= 10

    evidence = df[
        risky
        & (
            df["skin_score"]
            <= median_score
        )
    ].nsmallest(
        limit,
        "skin_score",
    )

    return sorted(
    evidence["recorded_at"].tolist()
)

def analyze_patterns(records):
    validate_records(records)

    record_days = len(records)
    confidence = get_confidence(record_days)

    if record_days < 7:
        return {
            "recordDays": record_days,
            "confidence": None,
            "impacts": [],
            "allImpacts": [],
            "evidenceDates": [],
            "reason": "NOT_ENOUGH_RECORDS",
            "needMore": 7 - record_days,
        }

    df = prepare_dataframe(records)

    # 기록이 적으면 lag 0~1만 사용
    # 14일 이상이면 lag 0~3 사용
    lags = (
        range(2)
        if record_days < 14
        else range(4)
    )

    calculated = []

    for factor, config in FACTOR_CONFIG.items():
        best = best_lag_correlation(
            df,
            config["column"],
            lags,
        )

        calculated.append({
            "factor": factor,
            "label": config["label"],
            "lag": best["lag"],
            "corr": best["corr"],
            "rawImpact": best["corr"] ** 2,
        })

    # 상관계수 제곱값을 이용해
    # 모든 impact의 합이 1이 되도록 정규화
    total = sum(
        item["rawImpact"]
        for item in calculated
    )

    for item in calculated:
        item["impact"] = (
            item["rawImpact"] / total
            if total
            else 0.0
        )

        del item["rawImpact"]

        item["corr"] = round(
            item["corr"],
            3,
        )

        item["impact"] = round(
            item["impact"],
            3,
        )

    calculated.sort(
        key=lambda item: item["impact"],
        reverse=True,
    )

    top_impacts = calculated[:3]
    top = top_impacts[0]

    return {
        "recordDays": record_days,
        "confidence": confidence,
        "impacts": top_impacts,
        "allImpacts": calculated,
        "evidenceDates": find_evidence_dates(
            df,
            top["factor"],
            top["lag"],
        ),
        "modelVersion": (
            "habitpattern-spearman-v1.0"
        ),
    }
