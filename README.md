# SkinLoop AI

생활습관 기록과 피부 상태의 연관성을 분석하고, 습관 변화에 따른 피부 점수 변화를 비교하는 SkinLoop의 AI 모듈입니다.

## 주요 기능

* 피부 상태 입력값 기반 피부 점수 계산
* Spearman 상관계수와 시차 기반 영향 요인 분석
* Ridge 회귀 기반 What-if 시나리오 비교
* 28일치 샘플 데이터 생성 및 분석 결과 검증

## 분석 흐름

```text
피부 상태·생활습관 입력
→ 피부 점수 계산
→ 주요 영향 요인 분석
→ 습관 변경 시나리오 비교
→ LLM을 통한 결과 문장화
```

LLM 결과 문장화는 추후 연동할 예정입니다.

## 프로젝트 구조

```text
data/
└─ seed_28days.json          # 28일치 생활습관·피부 기록과 완료 실험 샘플

docs/
├─ seed_validation.md        # 샘플 데이터와 분석 기능의 내부 검증 결과
├─ model_evaluation.md       # 28일 합성 데이터 내부 성능평가
└─ integration_contract.md   # 백엔드 연동 입력·출력 계약 초안

scripts/
├─ seed_generator.py         # 피부 점수 계산식을 적용한 샘플 데이터 생성
├─ evaluate_model.py         # 시간순 내부 성능평가
└─ validate_seed.py          # 데이터 형식과 전체 분석 결과 검증

src/
├─ __init__.py
├─ skin_score.py             # 공통 피부 점수 계산
├─ validation.py             # 계산 모듈 공통 입력 검증
├─ habit_pattern.py          # Spearman 상관계수와 시차 기반 영향 요인 분석
└─ whatif.py                 # Ridge 회귀 기반 습관 변경 시나리오 비교

tests/                       # 계산 모듈과 시드 데이터 자동 테스트

.gitignore                   # GitHub에 올리지 않을 파일 설정
README.md                    # 프로젝트 개요
requirements.txt             # Python 패키지 목록
requirements-dev.txt         # 테스트 패키지 목록
```

## 현재 구현 범위

현재 피부 점수 계산, 입력 검증, 영향 요인 분석, What-if 계산, 샘플 데이터 생성 및 자동 검증이 구현되어 있습니다.

검증은 `python -m pytest`, `python scripts/validate_seed.py`, `python scripts/evaluate_model.py`로 실행합니다.

LLM 결과 문장화와 실제 서비스 API 연결은 추후 진행할 예정입니다.

## 백엔드 연동

이 저장소는 계산·입력검증만 담당하는 순수 모듈이며, 별도 서비스로 띄우지 않습니다.

* **연동 방식**: 백엔드(FastAPI)가 이 저장소의 `src/`를 **vendoring(복사)** 해 같은 프로세스에서 직접 import 합니다.
  ```python
  from src.habit_pattern import analyze_patterns
  from src.whatif import run_whatif
  ```
  vendoring 대상은 `src/` 디렉터리 하나입니다. `src/`는 import 시 파일·네트워크 부작용이나 하드코딩 경로가 없고, 모든 내부 import가 절대경로 `src.*`라 복사만으로 동작합니다. (`scripts/`는 개발·검증용이라 복사 대상이 아닙니다.)
* **런타임 의존성**: `numpy`, `pandas`, `scipy`, `scikit-learn` (하한만 지정, `requirements.txt` 참조). 백엔드 의존성과 충돌하지 않도록 정확한 버전 핀은 사용하지 않습니다.
* **입출력 계약**: 입력 필드 형식·함수 시그니처·출력 키·책임 경계는 `docs/integration_contract.md`가 정본입니다. 피부 점수 계산식도 이 저장소의 `src/skin_score.py`를 정본으로 사용하고 백엔드에서 재구현하지 않습니다.
* **HTTP 응답 변환, camelCase↔snake_case 매핑, DB 조회·저장, LLM 문장화, 타임아웃·폴백**은 백엔드 연동 계층의 책임입니다.

## 주의사항

* 현재 결과는 28일치 합성 샘플 데이터를 이용한 MVP 내부 검증 결과입니다.
* 분석 결과는 인과관계나 의학적 진단이 아닌 생활습관 관리 참고 정보입니다.
