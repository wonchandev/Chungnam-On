# 🌾 충남온

충청남도 외국인 일용직 근로자를 위한 구인·구직 및 생활 지원 플랫폼

## 주요 기능

- **일용직 구인·구직:** 근무 날짜·일당·시간·지역 정보, 신청/승인 관리, 사업주 평판(온도)
- **일자리 지도:** 현재 위치 기반 주변 일자리 탐색, 지역·업종 필터
- **AI 행정·생활 지원:** 비자·건강보험·근로 정보 안내, AI 챗봇, 서류 작성 도움
- **외국인 근로자 커뮤니티:** 지역별 커뮤니티, 동행 모집, 후기·생활 정보 공유
- **다국어 번역:** 게시글 자동 번역, 채팅 번역, 현장 필수 표현

## 기술 스택

| 영역 | 스택 |
| --- | --- |
| Frontend | React |
| Backend | Django, Django REST Framework, JWT (SimpleJWT) |
| API 문서 | drf-spectacular + Scalar |
| DB | SQLite (로컬) / PostgreSQL (배포) |

## 프로젝트 구조

```text
Chungnam-On/
├── backend/     # Django REST API  (자세한 내용: backend/README.md)
├── frontend/    # React + Vite (자세한 내용: frontend/README.md)
└── .github/     # 이슈/PR 템플릿, 기여 가이드
```

## 백엔드 빠른 시작

```bash
cd backend
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

- API 문서 (Scalar): http://127.0.0.1:8000/docs
- 헬스체크: http://127.0.0.1:8000/api/health/

## 🌿 Git 브랜치 전략

안정적인 통합 개발과 배포를 위해 다음 브랜치 전략을 사용합니다.

| 브랜치 | 용도 |
| --- | --- |
| `main` | 최종 배포 코드 관리 |
| `develop` | 기능 통합 및 개발 코드 관리 |
| `feat/...` | 신규 기능 개발 |
| `refactor/...` | 코드 개선 및 리팩토링 |
| `fix/...` | 버그 수정 |

### 작업 흐름

1. `develop` 브랜치에서 작업용 브랜치를 생성합니다.
2. 담당 기능을 구현하고 의미 있는 단위로 커밋합니다.
3. 작업 브랜치를 원격 저장소에 푸시합니다.
4. `develop`을 대상으로 Pull Request(PR)를 생성합니다.
5. 변경 사항을 확인한 후 `develop`에 병합합니다.
6. 배포 준비가 완료되면 `develop`에서 `main`으로 PR을 생성합니다.
7. **`main` 병합 전에는 반드시 PM의 코드 리뷰 및 승인을 받아야 합니다.**
8. 승인 후 `main`에 병합하면 GitHub Actions를 통해 배포가 진행됩니다.

### ⚠️ 브랜치 관리 규칙

- `main` 브랜치에 직접 푸시하지 않습니다.
- PM 승인 없이 `main`에 병합하지 않습니다.
- 기능 개발은 별도의 작업 브랜치에서 진행합니다.
- 다른 팀원의 작업과 충돌하지 않도록 작업 내용을 사전에 공유합니다.
- 병합 전 변경 사항과 실행 결과를 확인합니다.

## 🤝 협업 규칙

모든 팀원은 실제 개발에 참여하고 GitHub 협업 기록을 남겨야 합니다.

- **Issue:** 구현할 기능과 작업 내용을 등록합니다.
- **Branch:** 작업 목적에 맞는 브랜치를 생성합니다.
- **Commit:** 변경 내용을 알 수 있도록 커밋 메시지를 작성합니다.
- **Pull Request:** 변경 사항, 테스트 결과 및 관련 Issue를 기록합니다.
- **Code Review:** 다른 팀원의 코드를 검토하고 개선 의견을 남깁니다.
- **Merge:** 리뷰와 확인이 완료된 코드를 적절한 브랜치에 병합합니다.

### 커밋 메시지 예시

```text
feat: 메인 페이지 레이아웃 구현
feat: 팀원 프로필 카드 추가
style: 모바일 화면 스타일 수정
fix: 프로젝트 링크 오류 수정
docs: README 프로젝트 소개 작성
refactor: 공통 메뉴 구조 개선
```

### Pull Request 규칙

PR에는 다음 내용을 포함합니다.

- 변경한 기능 및 작업 내용
- 수정한 파일
- 구현 결과 또는 화면 캡처
- 테스트 결과
- 관련 Issue 번호

## 배포 (Railway)

프론트 빌드와 Django(ASGI/WebSocket)를 한 서비스로 실행합니다. 루트의 `Dockerfile`·`railway.json`을 Railway가 자동 인식합니다.

1. Railway → New Project → Deploy from GitHub repo → 이 저장소(`main`) 선택
2. Variables 에 `SECRET_KEY`(임의의 긴 문자열), `OPENAI_API_KEY`(선택), `TRANSLATION_BACKEND=apps.translation.backends.MyMemoryTranslator`(선택) 입력
3. Settings → Networking → Generate Domain
4. (선택) 데이터 유지: Volume 을 `/data` 에 연결하고 `DATABASE_URL=sqlite:////data/db.sqlite3` 설정. 없으면 재배포 때 DB가 초기화되고 데모 데이터가 다시 생성됩니다.

시작 시 `migrate` → `seed_demo`(데모 계정 worker1/boss1~3, 비밀번호 `demo1234!`) → `index_guides`(OpenAI 키가 있을 때) 순서로 실행됩니다.
