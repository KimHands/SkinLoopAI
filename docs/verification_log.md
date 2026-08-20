# 검증 로그

vendoring 준비를 위한 재검증 기록. 상세 방법·해석은 `model_evaluation.md`, `seed_validation.md` 참조.

## 2026-08-19 — 최신 라이브러리 재검증

환경: Python 3.14.6 / numpy 2.5.2 / pandas 3.0.5 / scipy 1.18.0 / scikit-learn 1.9.0 / pytest 9.1.1

실행 명령과 결과:

| 명령 | 결과 |
|---|---|
| `python -m pytest -q` | **35 passed** (4.15s) |
| `python scripts/validate_seed.py` | **전항목 PASS** (exit 0) |
| `python scripts/evaluate_model.py` | **정상 실행** (exit 0) |

핵심 지표(문서 기준값과 동일):

- HabitPattern: 상위 3개 `sleep_short(lag1) → late_snack(lag1) → stress(lag0)`, lag 일치 3/3, confidence `high`
- Ridge walk-forward(14일): MAE 4.529 / RMSE 5.653 / 방향정확도 64.3% / 범위포함률 50.0%
- 기준 모델: 과거평균 MAE 9.981, 직전점수 MAE 7.214

문서 기준 환경(numpy 1.26.4 / pandas 2.2.2 / scipy 1.14.1 / scikit-learn 1.9.0)과
결과가 소수점 3자리까지 동일. Spearman·Ridge가 결정론적이고 시드 데이터가 고정이라
메이저 버전 점프(pandas 2.x→3.x)에서도 값이 바뀌지 않았다. → requirements.txt 핀 완화의 근거.

수정: 없음(검증 통과, 코드 변경 불필요).
