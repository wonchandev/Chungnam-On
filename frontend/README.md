# 충남온 Frontend

React + Vite + React Router 기반 초기 프로젝트입니다. 각 페이지는 기본 안내 화면이며 상세 디자인과 기능은 추후 구현 예정입니다.

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
