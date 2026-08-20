# SkinLoop AI — 프로젝트 종합 문서

> 생활습관 기록과 피부 상태의 연관성을 분석하고, 습관 변화에 따른 피부 점수 변화를 비교하는 SkinLoop의 AI 계산 모듈.
> 이 문서는 코드·데이터·연동 계약·검증 결과를 한 곳에 정리한 것이다. 세부 근거는 `docs/` 하위 개별 문서를 참조한다.

## 1. 한눈에 보기

- **역할**: 순수 계산 모듈. API·DB·LLM 호출을 하지 않는다. 입력을 받아 점수·패턴·시나리오를 계산하고 검증만 한다.
- **입력**: 날짜별 생활습관·피부 점수 기록 목록(`records`).
- **출력**: 피부 점수, 영향 요인 분석(`impacts`), What-if 시나리오 비교.
- **성숙도**: 28일 합성 샘플 1개로 내부 검증을 마친 MVP 단계. LLM 문장화·실서비스 API 연결은 미구현.
- **스택**: Python 3.12, NumPy, pandas, SciPy, scikit-learn.

분석 흐름:

```text
피부 상태·생활습관 입력
→ 피부 점수 계산 (skin_score)
→ 주요 영향 요인 분석 (habit_pattern)
→ 습관 변경 시나리오 비교 (whatif)
→ LLM 결과 문장화  ※ 추후 백엔드 연동
```

## 2. 아키텍처

```text
scripts/           실행·검증 진입점 (CLI)
  ├─ seed_generator.py   합성 샘플 생성
  ├─ evaluate_model.py   walk-forward 내부 성능평가
  └─ validate_seed.py    데이터 형식 + 분석 결과 검증

src/               계산 코어
  ├─ validation.py       공통 입력 검증 (모든 계산의 관문)
  ├─ skin_score.py       피부 점수 계산식 (정본)
  ├─ habit_pattern.py    Spearman 상관 + 시차(lag) 영향 요인 분석
  └─ whatif.py           Ridge 회귀 기반 시나리오 비교

data/seed_28days.json    28일 기록 + 완료 실험 샘플
tests/                   5개 파일, 자동 테스트
```

의존 방향: `scripts → src`, `habit_pattern·whatif → validation`. `whatif`는 `habit_pattern`의 `get_confidence`를 재사용한다. 순환 의존 없음.

## 3. 데이터 계약

### 3.1 공통 입력 `records`

날짜 오름차순 정렬이 가능한 기록 객체 목록. 각 필드는 계산 전 `validate_records`가 검증하며, 위반 시 `ValueError`를 발생시킨다.

| 필드 | 형식·범위 |
|---|---|
| `recorded_at` | 중복 없는 `YYYY-MM-DD` 문자열 |
| `sleep_hours` | 숫자, 0~14 |
| `late_snack` | boolean |
| `stress_level` | 정수, 1~5 |
| `exercise_min` | 정수, 0~300 |
| `cosmetic_changed` | boolean |
| `skin_score` | 숫자, 20~100 |

> 검증 세부: boolean은 숫자 필드로 허용되지 않고(`isinstance(bool)` 배제), 숫자는 유한값(`math.isfinite`)이어야 하며, `recorded_at`은 파싱 후 재직렬화가 원문과 일치해야 한다(엄격한 형식 검사).

샘플 데이터(`seed_28days.json`)는 위 필드에 더해 `skin_redness`, `skin_acne_count`, `skin_oiliness`, `photo_url`, `memo`를 포함하지만, 계산 모듈이 사용하는 것은 위 7개 필드다.

### 3.2 책임 경계

AI 저장소는 **점수·패턴·시나리오 계산과 입력 검증만** 담당한다. 다음은 모두 백엔드 연동 계층의 책임이다.

- HTTP 응답 변환, camelCase ↔ snake_case 매핑
- DB 조회·저장
- LLM 문장화
- 타임아웃·규칙 기반 폴백

## 4. 계산 모듈 상세

### 4.1 피부 점수 — `skin_score.calculate_skin_score(redness, acne, oiliness) → int`

- 입력: 각 1~5 정수(홍조·여드름·유분).
- 계산식(정본): `round(100 - ((redness + acne + oiliness - 3) / 12 × 80))`
- 의미: 세 지표가 모두 최상(합 3)이면 100점, 모두 최악(합 15)이면 20점. 백엔드는 이 식을 재구현하지 말고 이 모듈을 정본으로 사용한다.

### 4.2 영향 요인 분석 — `habit_pattern.analyze_patterns(records) → dict`

생활습관 5개 요인이 피부 점수에 미치는 상대적 영향을 Spearman 상관계수로 추정한다.

- **요인**: `sleep_short`(6시간 미만 수면), `late_snack`, `stress`, `exercise`, `cosmetic_changed`.
- **신뢰도(confidence)**: 기록일수 기준 — 7일 미만 `None`, 7~13일 `low`, 14~20일 `medium`, 21일 이상 `high`.
- **7일 미만**: 계산하지 않고 `NOT_ENOUGH_RECORDS` 구조(`needMore` 포함) 반환.
- **시차(lag)**: 7~13일은 lag 0~1, 14일 이상은 lag 0~3 비교. 요인별로 Spearman 상관 **절댓값**이 가장 큰 lag를 선택한다(전날 습관이 다음 날 피부에 반영되는 지연 효과 포착).
- **impact**: 선택된 상관계수의 제곱(`corr²`)을 전체 요인 합으로 정규화해 상대 기여도로 만든다(합 = 1).
- **evidenceDates**: 선택된 lag를 적용한 뒤 위험 습관이 있었고 `skin_score`가 중앙값 이하로 낮았던 날 중 최저 점수 3일. **위험 습관을 기록한 날이 아니라, 그 영향이 관찰된 날**이다.
- **출력 키**: `recordDays`, `confidence`, `impacts`(상위 3), `allImpacts`, `evidenceDates`, `modelVersion`(`habitpattern-spearman-v1.0`).

### 4.3 What-if 시나리오 — `whatif.run_whatif(records, target_habit, change_value) → dict`

특정 습관을 바꿨을 때의 피부 점수 변화를 Ridge 회귀로 비교한다.

- **최소 14일** 필요(미만이면 `NOT_ENOUGH_RECORDS`).
- **모델**: `StandardScaler` → `Ridge(alpha=3.0)` 파이프라인. 적은 데이터에서 비교적 안정적.
- **특징 구성**: 오늘 점수 예측에 **전날** 수면·야식과 **당일** 스트레스·운동·화장품 변경을 사용(첫날은 전날 없어 제외).
- **지원 습관·상한**(`change_value` 검증): `sleep_short`(≤14), `late_snack`(주당 감소 횟수, ≤7), `stress`(≤4), `exercise`(≤300). `change_value`는 0 초과·유한값.
- **출력 키**: `targetHabit`, `label`, `current`/`changed`(각 `range`+4주 `trend`), `direction`(`improve`/`worsen`/`unclear`, 임계 ±1점), `confidence`, `estimatedDifference`, `modelVersion`(`whatif-ridge-v1.0`).
- **해석 주의**: `estimatedDifference`는 같은 회귀 모델로 두 시나리오의 계산값을 비교한 값일 뿐, 실제 피부 변화 보장이나 의학적 예측이 아니다. `trend`도 주별 독립 예측이 아니라 4주 화면 표시용 비교 추세다.

## 5. 실행 방법

```bash
# (권장) 가상환경
python -m venv .venv && source .venv/bin/activate

# 의존성
pip install -r requirements.txt        # 런타임
pip install -r requirements-dev.txt    # 테스트 포함(pytest)

# 자동 테스트
python -m pytest

# 합성 샘플 생성 (기존 파일 있으면 --force 필요)
python scripts/seed_generator.py --force

# 데이터 형식 + 분석 결과 검증
python scripts/validate_seed.py

# 내부 성능평가(요약) / 상세
python scripts/evaluate_model.py
python scripts/evaluate_model.py --details
```

## 6. 검증·평가 결과 (2026-08-15, 28일 합성 샘플, seed=42)

### 패턴 분석 (심어둔 패턴 복원 확인)

| 순위 | 요인 | lag | corr | impact |
|---|---|---:|---:|---:|
| 1 | 6시간 미만 수면 | 1 | -0.755 | 0.417 |
| 2 | 야식 | 1 | -0.699 | 0.357 |
| 3 | 스트레스 | 0 | -0.468 | 0.160 |
| 4 | 운동 시간 | 3 | 0.220 | 0.035 |
| 5 | 화장품 변경 | 2 | -0.207 | 0.031 |

기대 순서(수면→야식→스트레스)와 일치, lag 3/3 일치, confidence `high`.

### Ridge 성능 (walk-forward, 14일 평가)

| 모델 | MAE | RMSE |
|---|---:|---:|
| Ridge | 4.529 | 5.653 |
| 과거 평균 | 9.981 | 12.972 |
| 직전 점수 | 7.214 | 10.899 |

방향 정확도 64.3%, 범위 포함률 50.0%. Ridge가 두 기준 모델보다 오차가 낮았다. `pytest` 35개 항목 통과.

## 7. 현재 한계와 다음 단계

- **일반화 미확인**: 결과는 합성 샘플 **1개**에 심은 패턴을 복원한 것으로, 실제 사용자 데이터 성능이 아니다. 날짜 구성·랜덤 시드에 민감할 수 있다.
- **인과 아님**: 상관·회귀 기반이라 인과관계나 의학적 진단이 아닌 생활습관 관리 참고 정보다.
- **범위 보수성**: What-if 범위 포함률 50%로 아직 충분히 보수적이지 않으나, 샘플 1개로 재조정하면 과적합 위험이 있어 이번 평가만으로 계산 방식을 바꾸지 않는다.
- **미구현**: LLM 결과 문장화, 실서비스 API 연동.
- **다음**: 별도 합성 데이터와 실제 파일럿 데이터 확보 후 동일 평가 재수행 → 범위·모델 재검토.

## 8. 관련 문서

| 문서 | 내용 |
|---|---|
| `README.md` | 프로젝트 개요·구조 |
| `docs/integration_contract.md` | 백엔드 연동 입력·출력 계약(정본 시그니처) |
| `docs/seed_validation.md` | 샘플 데이터·분석 기능 검증 결과 |
| `docs/model_evaluation.md` | walk-forward 내부 성능평가 방법·결과 |
