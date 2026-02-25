# WebStateForge

WebStateForge는 웹사이트의 UI 상태를 자동으로 탐색하고,  
상태를 기능 단위로 추상화하여 실행 가능한 Markdown DSL로 변환하는  
하이브리드 AI 기반 웹 상태 추상화 엔진입니다.

이 프로젝트는 OpenClaw 및 자율 브라우저 에이전트 학습을 위해 설계되었습니다.

---

## 🚀 주요 기능

- 🔍 Playwright 기반 상태 탐색
- 🧠 Rule + 경량 LLM 하이브리드 상태 분류
- 🕸 상태 그래프 생성
- 🛡 위험 버튼 자동 필터링 (delete / logout 등)
- 📉 API 비용 절감 캐시 시스템
- 🔁 Ollama API 자동 재시도 (Exponential Backoff)
- 📄 실행 가능한 Markdown DSL 자동 생성
- ⚡ OpenClaw 학습 최적화 설계

---

## 🧱 시스템 구조

```
브라우저 탐색
        ↓
Feature Vector 추출
        ↓
Rule 기반 1차 분류
        ↓
경량 LLM 보정
        ↓
상태 그래프 구성
        ↓
고성능 LLM DSL 생성
```

---

## 📦 요구사항

- Python 3.9 이상
- Ollama Cloud API Key

패키지 설치:

```
pip install -r requirements.txt
playwright install
```

---

## 🔐 API Key 설정

`webstateforge.py` 파일 상단에서 다음 부분을 수정합니다:

```
API_KEY = "YOUR_OLLAMA_API_KEY"
```

⚠ 주의  
공개 저장소에 실제 API Key를 업로드하지 마십시오.

---

## ▶ 실행 방법

```
python webstateforge.py
```

실행 흐름:

1. 분석할 URL 입력
2. 로그인 필요 시 브라우저에서 수동 로그인
3. 터미널에서 Enter 입력
4. 자동 탐색 수행
5. `state_graph.json` 생성
6. 선택 시 `site_profile.md` DSL 생성

---

## 📂 생성 파일 설명

### state_graph.json

탐색된 상태 구조 데이터입니다.

예시:

```
{
  "state_type": "list_view",
  "features": {
    "table_count": 1,
    "pagination": true
  },
  "actions": ["open_detail", "paginate_next"]
}
```

---

### site_profile.md

OpenClaw 실행용 Markdown DSL입니다.

예시:

```
# State: List_View
Type: list_view

Actions:
- open_detail:
    requires:
        - table_row
    result: detail_view
```

---

## 💰 API 비용 최적화 구조

- 모델 + 프롬프트 해시 기반 캐시
- `ollama_cache.json`에 영구 저장
- temperature = 0 (결정적 응답)
- 자동 재시도 시스템 내장

동일 요청은 재호출하지 않습니다.

---

## 🛡 안전 장치

다음 키워드가 포함된 버튼은 자동 차단됩니다:

- delete
- remove
- logout
- sign out
- 탈퇴
- 삭제

⚠ 반드시 테스트 환경에서 실행하세요.

---

## 🎯 활용 목적

- OpenClaw 학습용 사이트 프로파일 생성
- 자율 브라우저 에이전트 연구
- UI 상태 추상화 실험
- 웹 자동화 DSL 생성

---

## 📁 권장 프로젝트 구조

```
WebStateForge/
│
├── webstateforge.py
├── requirements.txt
├── README.md
├── ollama_cache.json
├── state_graph.json
└── site_profile.md
```

---

## 🔒 .gitignore 권장 항목

```
ollama_cache.json
state_graph.json
site_profile.md
__pycache__/
.env
```

---

## 📜 라이선스

MIT License
