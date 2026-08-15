import math
from collections.abc import Mapping, Sequence
from datetime import date
from numbers import Integral, Real


REQUIRED_RECORD_FIELDS = {
    "recorded_at",
    "sleep_hours",
    "late_snack",
    "stress_level",
    "exercise_min",
    "cosmetic_changed",
    "skin_score",
}

WHATIF_CHANGE_LIMITS = {
    "sleep_short": 14,
    "late_snack": 7,
    "stress": 4,
    "exercise": 300,
}


def _validate_real(
    name,
    value,
    minimum,
    maximum,
):
    if (
        not isinstance(value, Real)
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(
            f"{name}는 유한한 숫자여야 합니다."
        )

    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name}는 {minimum}~{maximum}여야 합니다."
        )


def _validate_integer(
    name,
    value,
    minimum,
    maximum,
):
    if (
        not isinstance(value, Integral)
        or isinstance(value, bool)
    ):
        raise ValueError(
            f"{name}는 정수여야 합니다."
        )

    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name}는 {minimum}~{maximum}여야 합니다."
        )


def validate_records(records):
    if (
        not isinstance(records, Sequence)
        or isinstance(records, (str, bytes))
    ):
        raise ValueError(
            "records는 기록 목록이어야 합니다."
        )

    seen_dates = set()

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(
                f"records[{index}]는 객체여야 합니다."
            )

        missing = (
            REQUIRED_RECORD_FIELDS
            - set(record)
        )

        if missing:
            raise ValueError(
                "필수 필드가 없습니다: "
                f"{sorted(missing)}"
            )

        recorded_at = record["recorded_at"]

        if not isinstance(recorded_at, str):
            raise ValueError(
                "recorded_at은 YYYY-MM-DD 문자열이어야 합니다."
            )

        try:
            parsed_date = date.fromisoformat(
                recorded_at
            )
        except ValueError as error:
            raise ValueError(
                "recorded_at은 유효한 YYYY-MM-DD여야 합니다."
            ) from error

        if parsed_date.isoformat() != recorded_at:
            raise ValueError(
                "recorded_at은 YYYY-MM-DD 형식이어야 합니다."
            )

        if recorded_at in seen_dates:
            raise ValueError(
                "recorded_at은 중복될 수 없습니다: "
                f"{recorded_at}"
            )

        seen_dates.add(recorded_at)

        _validate_real(
            "sleep_hours",
            record["sleep_hours"],
            0,
            14,
        )
        _validate_integer(
            "stress_level",
            record["stress_level"],
            1,
            5,
        )
        _validate_integer(
            "exercise_min",
            record["exercise_min"],
            0,
            300,
        )
        _validate_real(
            "skin_score",
            record["skin_score"],
            20,
            100,
        )

        for field in (
            "late_snack",
            "cosmetic_changed",
        ):
            if not isinstance(
                record[field],
                bool,
            ):
                raise ValueError(
                    f"{field}는 boolean이어야 합니다."
                )


def validate_whatif_request(
    target_habit,
    change_value,
):
    if target_habit not in WHATIF_CHANGE_LIMITS:
        raise ValueError(
            "지원하지 않는 습관입니다: "
            f"{target_habit}"
        )

    if (
        not isinstance(change_value, Real)
        or isinstance(change_value, bool)
        or not math.isfinite(float(change_value))
    ):
        raise ValueError(
            "change_value는 유한한 숫자여야 합니다."
        )

    if change_value <= 0:
        raise ValueError(
            "change_value는 0보다 커야 합니다."
        )

    maximum = WHATIF_CHANGE_LIMITS[
        target_habit
    ]

    if change_value > maximum:
        raise ValueError(
            "change_value가 허용 범위를 초과했습니다: "
            f"최대 {maximum}"
        )
