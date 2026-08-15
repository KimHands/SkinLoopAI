# SkinLoop AI 계산 모듈 연동 계약 초안

이 문서는 SkinLoop AI 계산 모듈과 백엔드 사이의 입력·출력 계약을 정의한다. 계산 모듈은 API, DB, LLM 호출을 담당하지 않는다.

## 공통 입력

`records`는 날짜 오름차순 정렬이 가능한 생활습관·피부 점수 객체 목록이다. 계산 모듈은 정렬 전 다음 필드를 검증한다.

| 필드 | 형식과 범위 |
|---|---|
| `recorded_at` | 중복 없는 `YYYY-MM-DD` 문자열 |
| `sleep_hours` | 숫자, 0~14 |
| `late_snack` | boolean |
| `stress_level` | 정수, 1~5 |
| `exercise_min` | 정수, 0~300 |
| `cosmetic_changed` | boolean |
| `skin_score` | 숫자, 20~100 |

잘못된 입력은 `ValueError`를 발생시킨다. 백엔드는 이를 API 오류 형식으로 변환한다.

## 피부 점수

```python
calculate_skin_score(redness, acne, oiliness) -> int
```

각 입력은 1~5 정수다. 계산식은 다음과 같으며 AI 저장소의 `src/skin_score.py`를 정본으로 사용한다.

```text
100 - ((redness + acne + oiliness - 3) / 12 × 80)
```

## HabitPattern

```python
analyze_patterns(records: list[dict]) -> dict
```

- 7일 미만이면 기존 `NOT_ENOUGH_RECORDS` 구조를 반환한다.
- 7~13일은 lag 0~1, 14일 이상은 lag 0~3을 비교한다.
- 요인별 Spearman 상관계수 절댓값이 가장 큰 lag를 선택한다.
- `corr²`을 전체 요인 기준으로 정규화해 impact를 계산한다.
- 정상 결과는 `recordDays`, `confidence`, `impacts`, `allImpacts`, `evidenceDates`, `modelVersion`을 유지한다.

`evidenceDates`는 위험 습관이 기록된 원래 날짜가 아니라, 선택된 lag를 적용한 뒤 낮은 `skin_score`가 관찰된 날짜다. 예를 들어 전날 수면 부족이 다음 날 피부 점수와 연결되면 다음 날이 근거 일자로 반환된다.

## What-if

```python
run_whatif(
    records: list[dict],
    target_habit: str,
    change_value: float,
) -> dict
```

- 최소 14일의 기록을 사용한다.
- `StandardScaler`와 `Ridge(alpha=3.0)` 구조를 유지한다.
- 지원 대상은 `sleep_short`, `late_snack`, `stress`, `exercise`다.
- 정상 결과는 `targetHabit`, `label`, `current`, `changed`, `direction`, `confidence`, `estimatedDifference`, `modelVersion`을 유지한다.

`estimatedDifference`는 현재 기록에 같은 회귀 모델을 적용해 두 시나리오의 계산값을 비교한 값이다. 실제 피부 점수 변화에 대한 보장이나 의학적 예측이 아니다. `trend`도 각 주를 독립적으로 예측한 값이 아니라 두 시나리오의 차이를 4주 화면에 나타내기 위한 비교 추세다.

## 책임 경계

AI 저장소는 점수·패턴·시나리오 계산과 입력 검증만 담당한다. HTTP 응답 변환, camelCase와 snake_case 매핑, DB 조회·저장, LLM 문장화, 타임아웃과 규칙 기반 폴백은 백엔드 연동 계층의 책임이다.
