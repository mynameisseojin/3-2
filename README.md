# 판매 데이터 AI 비서

판매 기록을 Firestore에 저장하고, 요약 통계를 바탕으로 질문에 답하는 개인 맞춤형 AI 웹 서비스입니다. 사용자는 웹 화면에서 판매 데이터를 관리하고, 저장된 데이터를 근거로 AI와 대화할 수 있습니다.

## 서비스 주소

-**프론트엔드 접속 주소** : https://3-2-frontend.vercel.app
-**백엔드 접속 주소**- : https://three-2-w47e.onrender.com/docs

## 주요 기능

- **데이터 기반 AI 채팅:** 판매 데이터와 요약 통계를 시스템 프롬프트에 넣어 GPT가 데이터에 근거해 답변합니다. 첫 요청에는 Render가 깨어나는 동안 시간이 걸릴 수 있습니다.
- **판매 데이터 관리:** 날짜, 상품, 판매량, 메모를 등록하고 목록을 확인하거나 화면에서 삭제할 수 있습니다. 백엔드에는 생성·조회·수정·삭제 API가 구현되어 있습니다.
- **데이터 요약:** 기록 기간과 건수, 상품별 총판매량·평균·최대·최소를 확인할 수 있습니다.
- **대화 기록:** 채팅을 Firestore에 자동 저장하고, 목록에서 이전 대화를 선택해 불러옵니다.

## 데이터

- **데이터 주제:** 상품별 판매 기록
- **기록 기간:** 2025년 12월~2026년 1월
- **저장 건수:** Firestore에 정리된 107건
- **상품:** 벽돌케이크, 피스타치오 초콜릿(소·대), 헤이즐넛 초콜릿(소·대), 밀카 초콜릿
- 일부 기록은 과제 요구량을 맞추기 위한 보충 데이터입니다. 해당 기록은 메모에 **“과제용 보충 데이터(실제 기록 아님)”**으로 표시합니다.

## 기술 스택

- **프론트엔드:** HTML, CSS, Vanilla JavaScript
- **백엔드:** Python, FastAPI, Uvicorn, Pydantic
- **데이터베이스:** Firebase Firestore (Firebase Admin SDK)
- **AI:** OpenAI API
- **배포:** Vercel(프론트엔드), Render(백엔드)


## 환경 변수 및 비밀값 관리

### 백엔드 환경 변수

| 변수 | 필수 여부 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | 필수 | OpenAI API 인증 키 |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | 배포 권장 | Firebase 서비스 계정 JSON 전체를 환경 변수 값으로 설정 |
| `FIREBASE_CREDENTIALS_PATH` | 선택 | 서비스 계정 JSON 파일 경로. 미설정 시 `backend/serviceAccountKey.json`을 기본 경로로 사용 |


```env
OPENAI_API_KEY=여기에_본인_OpenAI_API_키
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
```

Render에서는 Dashboard의 **Environment** 설정에 `OPENAI_API_KEY`와 `FIREBASE_SERVICE_ACCOUNT_JSON`을 등록합니다. JSON 값은 한 줄 형식으로 넣고, 키 내용을 소스 코드나 README에 기록하지 않습니다.

### 보안 주의

- `.env`, `serviceAccountKey.json`, API 키를 GitHub에 커밋하지 않습니다.
- 비밀값은 로컬 환경 파일 또는 Render의 환경 변수 설정에만 둡니다.
- 실수로 키를 공개 저장소에 올렸다면 파일을 삭제하는 것만으로 끝내지 말고 해당 키를 폐기·재발급합니다.

## 로컬 실행 방법

아래 명령은 저장소 루트에서 실행합니다.

```bash
cd sales-assistant/sales-assistant/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`backend/.env`와 Firebase 인증 설정을 준비한 뒤 서버를 실행합니다.

```bash
uvicorn main:app --reload
```

- API 기본 주소: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- 프론트엔드를 로컬에서 테스트할 경우, 프론트엔드의 `API_BASE`를 로컬 주소로 설정하고 로컬 서버와 함께 실행해야 합니다.
