# 충남온 Frontend

React + Vite + React Router 기반 프로젝트입니다. 홈은 Figma 디자인에 맞춰 구현되어 있으며 Django API에서 공고를 조회합니다. 나머지 페이지는 각 담당자가 작업 중입니다.

## 홈 API 연결

백엔드를 `http://127.0.0.1:8000`에서 실행하면 Vite가 `/api`와 `/media` 요청을 전달합니다. 프론트에서 Google/OpenAI 키를 설정할 필요는 없습니다. 다른 서버를 사용하면 `.env.example`을 참고해 `.env`를 작성하세요.

- 기본 홈: `GET /api/jobs/ticker/`, `/api/jobs/urgent/`, `/api/jobs/recommended/`
- 지역 목록: `GET /api/regions/?level=sigungu`
- 지역 선택·검색: `GET /api/jobs/?region=...&q=...` (지역 선택 시 추천 영역은 해당 지역 최신 공고, 긴급 영역은 해당 지역 `urgent=true` 공고)
- 카드 클릭: `GET /api/jobs/{id}/`로 상세 다이얼로그 표시
- 관심 공고: `POST/DELETE /api/jobs/{id}/bookmark/`. 비로그인 시 홈의 로그인 다이얼로그를 표시합니다.
- 로그인: `/api/auth/login/`, `/api/auth/refresh/`, `/api/auth/logout/`. 홈 전용 임시 세션은 `sessionStorage`의 `chungnam-home-session`에 보관합니다. 공통 로그인 페이지 구현 시 이 저장소와 로그인 진입점을 통합하세요.

공고가 없으면 빈 목록을, 서버에 연결할 수 없으면 오류와 재시도 버튼을 표시합니다. 화면에 샘플 공고를 대신 노출하지 않습니다. 기본 추천은 백엔드의 규칙 기반 추천이며, 신규 공고는 홈 진입·지역 변경 시 조회합니다.

운영 빌드에서는 서버에서 `/api`·`/media`를 백엔드로 프록시하거나, 빌드 시 `VITE_API_BASE_URL`에 전체 API 주소를 지정하고 Django의 CORS에 프론트 주소를 허용해야 합니다. Vite 개발 프록시는 운영 정적 호스팅에 포함되지 않습니다.

API 클라이언트 검증: `npm test`. 전체 검사: `npm run lint`, `npm run build`.

## 실행

Node.js 22.12 이상(22.x) 또는 20.19 이상(20.x)을 사용하세요.

```bash
cd frontend
npm install
npm run dev
```

터미널에 표시되는 로컬 주소로 접속합니다.

검증: `npm run lint`, `npm run build`
빌드 미리보기: `npm run preview`

## 라우팅

| 경로              | 페이지         | 소스                                 |
| ----------------- | -------------- | ------------------------------------ |
| `/`               | 홈             | `src/pages/Home/index.jsx`           |
| `/communication`  | 다국어 소통    | `src/pages/Communication/index.jsx`  |
| `/administration` | 행정 관리      | `src/pages/Administration/index.jsx` |
| `/nearby-jobs`    | 내 주변 일자리 | `src/pages/NearbyJobs/index.jsx`     |
| `/jobs`           | 구인구직       | `src/pages/Jobs/index.jsx`           |

`src/App.jsx`에서 라우트를 관리하고, 공통 헤더와 메뉴는 `src/components/Header.jsx`, `src/components/Navigation.jsx`에서 관리합니다. 정의되지 않은 경로에는 404 화면을 표시합니다.

BrowserRouter를 사용하므로 배포 시 하위 경로 직접 접근과 새로고침을 지원하도록 서버에서 SPA 요청을 `index.html`로 연결해야 합니다.

## 컴포넌트 구조

페이지 진입점은 `src/pages/페이지명/index.jsx`입니다. 페이지 전용 컴포넌트는 필요할 때 해당 페이지 폴더 아래 `components/`에 추가하고, 여러 페이지에서 함께 쓰는 컴포넌트는 `src/components/`에 둡니다.

홈은 `src/pages/Home/` 아래에서 역할별로 나눕니다.

```text
Home/
├── index.jsx                # 페이지 상태와 컴포넌트 조합
├── components/              # 지역 선택, 툴바, 검색, 피드, 공고 카드, 다이얼로그
│   ├── RegionPicker.jsx
│   └── RegionPicker.css     # 지역 선택 컴포넌트 전용 스타일
├── hooks/                   # API 로딩·재시도, 로그인 세션
├── api/home.js              # 홈 전용 API
├── utils/formatters.js      # 금액·급여 유형·마감 표시
└── styles/home.css          # 홈 페이지 스타일
```

공통 HTTP 클라이언트는 `src/api/client.js`, 해당 테스트는 `src/api/__tests__/`에 둡니다. 다른 페이지를 구현할 때도 페이지 전용 UI는 그 페이지의 `components/`로 분리하고, 공통 헤더·내비게이션·본문 레이아웃은 유지합니다.
