# Frontend 가이드

## 1. 개요

`frontend`는 Work Order와 Robot 실행 상태를 관리하는 정적 웹 대시보드다. 별도의 빌드 도구나 npm 의존성 없이 HTML, CSS, JavaScript로 구성되며 Flask Backend가 화면과 정적 파일을 제공한다.

현재 화면은 다음 기능을 제공한다.

- Dashboard의 실행 대기·진행 중 Work Order 조회 및 제어
- Work Execution 성공률과 Robot 상태 조회
- `ERROR` Robot 복구 요청
- 최근 로그 조회
- Work Order 생성, `READY` 전환, 실행 및 강제 정지
- Work Order별 진행률과 현재 Operation 조회
- Work Execution과 Operation Execution별 이력 및 로그 조회
- API 성공·오류·빈 결과 상태 표시

---

## 2. 파일 구성

```text
frontend/
├── index.html    # 3개 View, Work Order 생성 Modal 및 화면 구조
├── app.js        # API 호출, 상태별 제어, Polling 및 DOM 렌더링
├── styles.css    # Dashboard, Card, Modal 및 반응형 스타일
└── README.md
```

Flask는 다음 경로로 파일을 제공한다.

```text
GET /                    → frontend/index.html
GET /static/app.js       → frontend/app.js
GET /static/styles.css   → frontend/styles.css
```

---

## 3. 화면 구조

```text
Dashboard
├── 현재 작업: READY·RUNNING Work Order
├── Work Execution 성공률
├── Robot Status
└── 최근 로그

Work Detail
└── 전체 Work Order와 상태별 실행 제어

History
├── Work Execution 선택
├── Operation Execution 선택
├── 선택한 Operation 실행 요약
└── 전체·Work·Operation 로그
```

### Dashboard

현재 작업에는 `READY`와 `RUNNING` Work Order만 표시한다. `RUNNING`을 먼저, 같은 상태에서는 priority 숫자가 작은 작업을 먼저 정렬한다.

- `READY`: `IDLE` Robot을 선택해 실행
- `RUNNING`: 진행률과 현재 Operation을 확인하고 강제 정지 요청
- 성공률: 종료된 Work Execution 중 `COMPLETED / (COMPLETED + FAILED + CANCELLED)` 비율
- Robot Status: 현재 상태와 활성 Work Execution 표시
- Robot 복구: `ERROR` Robot에만 복구 버튼 표시
- 최근 로그: 최신 5개 로그 표시

### Work Detail

전체 Work Order를 표시하고 상태에 맞는 제어를 제공한다.

| Work Order 상태 | 제공 동작 |
| --- | --- |
| `CREATED` | 작업 준비: `READY`로 전환 |
| `READY` | `IDLE` Robot 선택 후 실행 |
| `RUNNING` | 진행률·현재 Operation 표시 및 강제 정지 |
| `COMPLETED`, `FAILED`, `CANCELLED` | 종료 상태와 실행 결과 확인 |

### History

Work Execution을 선택하면 해당 Operation Execution 목록을 불러온다. Operation Execution을 선택하면 sequence, 상태, 시작·종료 시간을 표시하고 로그를 해당 실행으로 좁힌다.

로그 필터 우선순위는 다음과 같다.

```text
Operation Execution 선택 → operation_execution_id
Work Execution만 선택    → work_execution_id
선택 없음                 → 최근 전체 로그
```

---

## 4. Work Order 생성 Modal

Dashboard와 Work Detail의 `+ Work Order` 버튼으로 Modal을 연다.

| 필드 | 필수 여부 | Frontend 검증 |
| --- | --- | --- |
| Order Number | 필수 | 빈 문자열 불가, 최대 50자 |
| Title | 필수 | 빈 문자열 불가, 최대 300자 |
| Installation ID | 필수 | 1 이상의 정수 |
| Priority | 필수 | 1 이상의 정수, 기본값 3 |
| Remark | 선택 | 문자열 |
| Created By | 선택 | 최대 100자 |

Modal은 닫기 버튼, 취소 버튼, 배경 클릭 또는 `Escape` 키로 닫을 수 있다. 생성이 성공하면 Form을 초기화하고 Work Order 목록을 즉시 다시 조회한다. Dashboard 집계와 Robot 상태는 다음 3초 자동 갱신 주기에 반영된다.

---

## 5. Backend API

Frontend는 동일 Origin의 API를 사용한다.

| Method | Path | 사용 화면과 용도 |
| --- | --- | --- |
| `GET` | `/api/v1/dashboard` | Dashboard 성공률과 Robot 상태 |
| `GET` | `/api/v1/work-orders` | Dashboard·Work Detail 목록 |
| `GET` | `/api/v1/work-orders/{id}/progress` | Work Order 실행 진행률 |
| `POST` | `/api/v1/work-orders` | Work Order 생성 |
| `PATCH` | `/api/v1/work-orders/{id}` | `CREATED → READY` 전환 |
| `POST` | `/api/v1/work-orders/{id}/execute` | 선택한 Robot으로 실행 |
| `POST` | `/api/v1/work-orders/{id}/stop` | 실행 중인 Work 강제 정지 |
| `POST` | `/api/v1/robots/{id}/recover` | `ERROR` Robot 복구 |
| `GET` | `/api/v1/executions/work-executions` | History의 Work Execution 목록 |
| `GET` | `/api/v1/executions/work-executions/{id}/operations` | History의 Operation Execution 목록 |
| `GET` | `/api/v1/logs?limit=5` | Dashboard 최근 로그 |
| `GET` | `/api/v1/logs?limit=100&work_execution_id={id}` | Work Execution 로그 |
| `GET` | `/api/v1/logs?limit=100&operation_execution_id={id}` | Operation Execution 로그 |

`GET /api/v1/sensor-data`는 Backend에 구현돼 있지만 현재 Frontend에서는 호출하지 않는다. API 요청·응답과 상태 전이 규칙은 [Backend 개발 가이드](../app/README.md)를 참고한다.

---

## 6. 자동 갱신

`app.js`는 페이지 로드 시 Dashboard, Work Order, 로그, History의 Work Execution 목록을 불러온다. 이후 3초마다 다음 데이터를 갱신한다.

- Dashboard 성공률과 Robot 상태
- Work Order 목록과 각 Work Order 진행률
- Dashboard 최근 로그
- 현재 History 필터에 해당하는 로그

History의 Work Execution 선택 목록과 Operation Execution 선택 목록은 3초 Polling 대상이 아니다. 새 실행을 목록에 반영하려면 페이지를 다시 열고, Operation 목록은 Work Execution을 다시 선택한다.

---

## 7. 실행

모든 명령은 `web_app`에서 실행한다.

```bash
source .venv/bin/activate
python run.py
```

브라우저에서 `http://localhost:5000/`으로 접속한다. HTML 파일을 직접 열면 `/static/...`과 `/api/...` 절대 경로가 정상 동작하지 않으므로 Flask를 통해 접속해야 한다.

---

## 8. 수정 시 확인사항

- HTML의 `id`와 Navigation의 `data-view`를 변경하면 `app.js`의 DOM 조회 코드도 함께 변경한다.
- 상태별 버튼 조건을 변경할 때 Backend의 상태 전이 검증도 함께 확인한다.
- Polling 주기나 대상을 변경할 때 중복 요청과 중복 Timer가 생기지 않는지 확인한다.
- API 오류의 `error.message`가 Alert 또는 화면에 표시되므로 사용자에게 노출 가능한 문구인지 확인한다.
- 서버에서 받은 문자열은 `textContent`로 렌더링하는 방식을 유지한다.
- Modal을 변경할 때 Focus, `Escape`, 배경 클릭과 `body.modal-open` 처리를 함께 확인한다.
- History selector의 선택 ID와 로그 Query Parameter가 동기화되는지 확인한다.
- 상태값을 추가하면 Card, Badge, Button과 관련 CSS selector를 함께 갱신한다.
- 별도 Frontend 서버를 도입하면 API 주소와 CORS 정책을 다시 설정해야 한다.

---

## 9. 검증 체크리스트

- `/`에서 Dashboard, Work Detail, History를 이동할 수 있다.
- Dashboard에 `READY`·`RUNNING` Work와 성공률, Robot 상태, 최근 로그가 표시된다.
- Work Order Modal을 열고 닫을 수 있으며 새 Work Order 생성 후 목록이 갱신된다.
- `CREATED` Work Order를 `READY`로 전환할 수 있다.
- `READY` Work Order에 `IDLE` Robot을 선택해 실행할 수 있다.
- `RUNNING` Work Order의 진행률과 현재 Operation이 자동 갱신된다.
- 실행 중 작업의 강제 정지 요청과 확인 Dialog가 동작한다.
- `ERROR` Robot의 복구 버튼과 확인 Dialog가 동작한다.
- History에서 Work Execution과 Operation Execution을 선택하면 요약과 필터링된 로그가 표시된다.
- 빈 목록과 Backend 오류가 각 영역에 올바르게 표시된다.
- 좁은 화면에서 Sidebar, Card, Form과 Modal을 사용할 수 있다.
