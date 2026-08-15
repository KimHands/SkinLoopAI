def calculate_skin_score(
    redness,
    acne,
    oiliness,
):
    values = {
        "redness": redness,
        "acne": acne,
        "oiliness": oiliness,
    }

    for name, value in values.items():
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
        ):
            raise ValueError(
                f"{name}는 정수여야 합니다."
            )

        if not 1 <= value <= 5:
            raise ValueError(
                f"{name}는 1~5여야 합니다."
            )

    severity_sum = redness + acne + oiliness

    return round(
        100
        - (
            (severity_sum - 3)
            / 12
            * 80
        )
    )
