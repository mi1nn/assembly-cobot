# Frontend 가이드

## 개요

`frontend`는 Work Order를 관리하는 정적 웹 대시보드다. 별도의 빌드 도구나 npm 의존성 없이 HTML, CSS, JavaScript로 구성되며 Flask Backend가 화면과 정적 파일을 제공한다.

현재 제공 기능:

- Work Order 목록 조회 및 새로고침
- Work Order 생성
- Work Order 상태 변경
- 요청 성공 및 오류 메시지 표시

Robot Status 영역은 현재 API와 연결되지 않은 고정 표시다.

## 파일 구성

```text
frontend/
├── index.html    # 화면 구조와 입력 Form
├── app.js        # API 호출, 상태 변경 및 DOM 렌더링
├── styles.css    # 화면 스타일
└── README.md
```

Flask는 다음 경로로 파일을 제공한다.

```text
GET /                    → frontend/index.html
GET /static/app.js       → frontend/app.js
GET /static/styles.css   → frontend/styles.css
```

## 실행

모든 명령은 `web_app`에서 실행한다.

```bash
source .venv/bin/activate
python run.py
```

브라우저에서 다음 주소로 접속한다.

```text
http://localhost:5000/
```

HTML 파일을 직접 열면 `/static/...`과 `/api/...` 절대 경로가 정상 동작하지 않으므로 Flask를 통해 접속한다.

## Backend API

Frontend는 동일한 Origin의 Work Order API를 사용한다.

| Method | Path | 용도 |
| --- | --- | --- |
| `GET` | `/api/v1/work-orders` | 목록 조회 |
| `POST` | `/api/v1/work-orders` | Work Order 생성 |
| `PATCH` | `/api/v1/work-orders/{id}` | 상태 변경 |

API 요청과 응답 형식은 [Backend 개발 가이드](../app/README.md), 상세 검증 절차는 [Backend API 검증 가이드](../docs/backend_api_test.md)를 참고한다.

## 수정 시 확인사항

- HTML의 `id`를 변경하면 `app.js`의 DOM 조회 코드도 함께 변경한다.
- API 오류 응답은 `error.message`가 화면에 표시될 수 있으므로 사용자에게 노출 가능한 문구인지 확인한다.
- 서버에서 받은 문자열은 `textContent`로 렌더링하는 방식을 유지한다.
- 별도 Frontend 서버를 도입하면 API 주소와 CORS 정책을 다시 설정해야 한다.

기본 확인 항목:

- `/`가 정상적으로 열린다.
- Work Order 목록이 표시된다.
- 새 Work Order를 생성하면 목록이 갱신된다.
- 상태를 변경하고 저장하면 변경값이 반영된다.
- Backend 오류 시 화면에 오류 메시지가 표시된다.
