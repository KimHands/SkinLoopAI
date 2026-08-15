import pytest

from src.skin_score import calculate_skin_score


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((1, 1, 1), 100),
        ((3, 3, 3), 60),
        ((5, 5, 5), 20),
        ((4, 3, 4), 47),
    ],
)
def test_calculate_skin_score(values, expected):
    assert calculate_skin_score(*values) == expected


@pytest.mark.parametrize(
    "values",
    [
        (0, 1, 1),
        (6, 1, 1),
        (1.5, 1, 1),
        ("1", 1, 1),
        (True, 1, 1),
        (None, 1, 1),
    ],
)
def test_calculate_skin_score_rejects_invalid_values(
    values,
):
    with pytest.raises(ValueError):
        calculate_skin_score(*values)
