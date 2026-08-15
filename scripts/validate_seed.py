import json
import sys
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

sys.path.insert(
    0,
    str(ROOT),
)

from src.habit_pattern import analyze_patterns
from src.whatif import run_whatif


def load_seed_data():
    seed_path = (
        ROOT
        / "data"
        / "seed_28days.json"
    )

    with seed_path.open(
        encoding="utf-8"
    ) as file:
        return json.load(file)


def average(records):
    total = sum(
        record["skin_score"]
        for record in records
    )

    return round(
        total / len(records),
        1,
    )


def main():
    seed_data = load_seed_data()
    records = seed_data["records"]

    pattern_result = (
        analyze_patterns(records)
    )

    whatif_result = run_whatif(
        records=records,
        target_habit="sleep_short",
        change_value=1.0,
    )

    print("[패턴 분석 결과]")

    print(
        json.dumps(
            pattern_result,
            ensure_ascii=False,
            indent=2,
        )
    )

    print("\n[What-if 결과]")

    print(
        json.dumps(
            whatif_result,
            ensure_ascii=False,
            indent=2,
        )
    )

    top_impacts = (
        pattern_result["impacts"]
    )

    all_impacts = (
        pattern_result["allImpacts"]
    )

    impact_map = {
        item["factor"]: item["impact"]
        for item in all_impacts
    }

    bad_average = average(
        records[10:20]
    )

    recovery_average = average(
        records[20:28]
    )

    recovery_difference = round(
        recovery_average - bad_average,
        1,
    )

    checks = {
        "impacts 1위가 sleep_short": (
            top_impacts[0]["factor"]
            == "sleep_short"
        ),
        "impacts 2위가 late_snack": (
            top_impacts[1]["factor"]
            == "late_snack"
        ),
        "운동 impact가 0.1 미만": (
            impact_map["exercise"]
            < 0.1
        ),
        "화장품 변경 impact가 0.1 미만": (
            impact_map[
                "cosmetic_changed"
            ] < 0.1
        ),
        "confidence가 high": (
            pattern_result["confidence"]
            == "high"
        ),
        "수면 +1시간이 improve": (
            whatif_result["direction"]
            == "improve"
        ),
        "회복 평균이 악화 평균보다 "
        "8점 이상 높음": (
            recovery_difference >= 8
        ),
    }

    print("\n[구간 평균]")

    print(
        f"악화 구간: "
        f"{bad_average}점"
    )

    print(
        f"회복 구간: "
        f"{recovery_average}점"
    )

    print(
        f"회복 상승 폭: "
        f"{recovery_difference}점"
    )

    print("\n[최종 검증 결과]")

    for name, passed in checks.items():
        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(f"{status}: {name}")

    if all(checks.values()):
        print(
            "\n모든 검증을 통과했습니다."
        )

    else:
        print(
            "\n일부 검증 항목을 "
            "확인해야 합니다."
        )


if __name__ == "__main__":
    main()