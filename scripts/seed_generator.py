import argparse
import json
import random
import sys
from datetime import date, timedelta
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

from src.skin_score import calculate_skin_score


SEED = 42
DAYS = 28
DEFAULT_OUTPUT = ROOT / "data" / "seed_28days.json"

SHORT_SLEEP_DAYS = {10, 11, 13, 14, 15, 18}
LATE_SNACK_DAYS = {10, 12, 13, 15, 17, 19, 25}
COSMETIC_CHANGE_DAYS = {3, 14, 24}

STRESS_LEVELS = [
    2, 1, 3, 2, 1, 4, 2, 1, 3, 2,
    5, 2, 4, 2, 5, 3, 4, 2, 5, 3,
    3, 2, 4, 1, 3, 2, 4, 2,
]

def make_skin(target_score, rng):
    severity_sum = round(
        3 + (100 - target_score) / 80 * 12
    )
    severity_sum = max(3, min(15, severity_sum))

    base, remainder = divmod(severity_sum, 3)

    values = [
        base + 1 if i < remainder else base
        for i in range(3)
    ]

    rng.shuffle(values)

    return values


def make_habit(day, rng):
    if day in SHORT_SLEEP_DAYS:
        sleep = rng.uniform(4.5, 5.5)
    elif day < 10:
        sleep = rng.uniform(7.0, 8.0)
    elif day < 20:
        sleep = rng.uniform(6.4, 7.2)
    else:
        sleep = rng.uniform(6.5, 7.5)

    return {
        "sleep_hours": round(sleep, 1),
        "late_snack": day in LATE_SNACK_DAYS,
        "stress_level": STRESS_LEVELS[day],
        "exercise_min": rng.choice([0, 10, 20, 30, 40]),
        "cosmetic_changed": day in COSMETIC_CHANGE_DAYS,
    }


def make_records(today, rng):
    habits = [
        make_habit(day, rng)
        for day in range(DAYS)
    ]

    records = []
    previous_score = 75

    for day, habit in enumerate(habits):
        if day == 0:
            expected = 76 - (
                habit["stress_level"] - 2
            )
        else:
            previous_habit = habits[day - 1]

            sleep_penalty = (
                21
                if previous_habit["sleep_hours"] < 6
                else 0
            )

            snack_penalty = (
                16
                if previous_habit["late_snack"]
                else 0
            )

            stress_penalty = (
                habit["stress_level"] - 2
            )

            expected = (
                76
                - sleep_penalty
                - snack_penalty
                - stress_penalty
            )

        target = (
            0.7 * expected
            + 0.3 * previous_score
            + rng.uniform(-1.5, 1.5)
        )

        # 회복 구간에도 이전 악화 영향이 일부 남도록 설정
        if day >= 20:
            target -= 2

        redness, acne, oiliness = make_skin(
            target,
            rng,
        )

        score = calculate_skin_score(
            redness,
            acne,
            oiliness,
        )

        recorded_at = (
            today
            - timedelta(days=DAYS - 1 - day)
        ).isoformat()

        records.append({
            "recorded_at": recorded_at,
            **habit,
            "skin_redness": redness,
            "skin_acne_count": acne,
            "skin_oiliness": oiliness,
            "skin_score": score,
            "photo_url": None,
            "memo": None,
        })

        previous_score = score

    return records


def average(records):
    total = sum(
        record["skin_score"]
        for record in records
    )

    return round(total / len(records), 1)


def make_experiment(records):
    experiment_records = records[-14:]

    baseline = average(records[10:14])
    result = average(experiment_records[-7:])
    difference = result - baseline

    if difference >= 5:
        verdict = "improved"
    elif abs(difference) < 5:
        verdict = "no_change"
    else:
        verdict = "needs_more"

    return {
        "target_habit": "sleep_short",
        "title": "수면시간 1시간 늘리기",
        "duration_days": 14,
        "status": "done",
        "baseline_score": baseline,
        "result_score": result,
        "verdict": verdict,
        "started_at": (
            experiment_records[0]["recorded_at"]
        ),
        "ended_at": (
            experiment_records[-1]["recorded_at"]
        ),
    }


def make_seed_data(today):
    rng = random.Random(SEED)
    records = make_records(today, rng)

    return {
        "records": records,
        "experiments": [
            make_experiment(records)
        ],
    }


def write_seed_data(
    data,
    output,
    force=False,
):
    output = Path(output)

    if output.exists() and not force:
        raise FileExistsError(
            "출력 파일이 이미 있습니다. "
            "덮어쓰려면 --force를 사용하세요: "
            f"{output}"
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "날짜는 YYYY-MM-DD 형식이어야 합니다."
        ) from error


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="SkinLoop 28일치 합성 샘플 생성",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="생성할 JSON 경로",
    )
    parser.add_argument(
        "--today",
        type=parse_date,
        default=date.today(),
        help="샘플 마지막 날짜 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 출력 파일 덮어쓰기",
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    data = make_seed_data(args.today)
    records = data["records"]

    write_seed_data(
        data,
        args.output,
        force=args.force,
    )

    experiment = data["experiments"][0]

    print(f"생성 완료: {args.output}")
    print(
        f"양호 {average(records[:10])} / "
        f"악화 {average(records[10:20])} / "
        f"회복 {average(records[20:])}"
    )
    print(
        f"실험 {experiment['baseline_score']} → "
        f"{experiment['result_score']} "
        f"({experiment['verdict']})"
    )


if __name__ == "__main__":
    main()
