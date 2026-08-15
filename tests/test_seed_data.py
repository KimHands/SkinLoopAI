import json
from datetime import date
from pathlib import Path

import pytest

from scripts.seed_generator import (
    make_seed_data,
    parse_args,
    write_seed_data,
)
from src.skin_score import calculate_skin_score


ROOT = Path(__file__).resolve().parent.parent


def load_seed_data():
    with (
        ROOT / "data" / "seed_28days.json"
    ).open(encoding="utf-8") as file:
        return json.load(file)


def test_committed_seed_has_expected_shape_and_scores():
    data = load_seed_data()

    assert len(data["records"]) == 28
    assert len(data["experiments"]) == 1

    for record in data["records"]:
        expected = calculate_skin_score(
            record["skin_redness"],
            record["skin_acne_count"],
            record["skin_oiliness"],
        )
        assert record["skin_score"] == expected


def test_make_seed_data_uses_selected_today():
    data = make_seed_data(date(2026, 8, 15))

    assert data["records"][0]["recorded_at"] == (
        "2026-07-19"
    )
    assert data["records"][-1]["recorded_at"] == (
        "2026-08-15"
    )


def test_parse_args_supports_output_today_and_force(
    tmp_path,
):
    output = tmp_path / "custom-seed.json"
    args = parse_args([
        "--output",
        str(output),
        "--today",
        "2026-08-15",
        "--force",
    ])

    assert args.output == output
    assert args.today == date(2026, 8, 15)
    assert args.force is True


def test_write_seed_data_requires_force_for_existing_file(
    tmp_path,
):
    output = tmp_path / "seed.json"
    data = make_seed_data(date(2026, 8, 15))

    write_seed_data(data, output)

    with pytest.raises(FileExistsError):
        write_seed_data(data, output)

    write_seed_data(
        data,
        output,
        force=True,
    )

    saved = json.loads(
        output.read_text(encoding="utf-8")
    )
    assert saved == data
