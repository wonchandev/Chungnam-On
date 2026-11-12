# 충남온 Backend (Django REST API)

React 프론트엔드와 분리된 REST API 서버입니다. 인증은 **JWT (Bearer)** 를 사용합니다.

## 시작하기

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # 값 수정 (기본은 SQLite)
python manage.py migrate
python manage.py createsuperuser   # 선택
python manage.py runserver
```

| 주소 | 설명 |
| --- | --- |
| http://127.0.0.1:8000/docs | **Scalar API 문서** |
| http://127.0.0.1:8000/api/schema/ | OpenAPI 스키마 (JSON/YAML) |
| http://127.0.0.1:8000/api/health/ | 헬스체크 |
| http://127.0.0.1:8000/admin/ | Django 관리자 |

## 환경 변수 (`.env`)

| 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `SECRET_KEY` | Django 시크릿 키 (배포 시 반드시 변경) | dev 키 |
| `DEBUG` | 디버그 모드 | `False` |
| `ALLOWED_HOSTS` | 쉼표 구분 호스트 | 빈 값 |
| `CORS_ALLOWED_ORIGINS` | React 개발 서버 주소 (쉼표 구분) | 빈 값 |
| `DATABASE_URL` | 예: `postgres://user:pw@localhost:5432/db` | SQLite |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | 토큰 만료 | 30분 / 7일 |

## 인증 (JWT)

| Method | Endpoint | 설명 |
| --- | --- | --- |
| POST | `/api/auth/register/` | 회원가입 (`role`: worker / employer) |
| POST | `/api/auth/login/` | 로그인 → `access`, `refresh` 발급 |
| POST | `/api/auth/refresh/` | access 토큰 재발급 (refresh 는 회전됨) |
| GET/PATCH | `/api/auth/me/` | 내 정보 조회/수정 |

인증이 필요한 API 는 헤더에 `Authorization: Bearer <access>` 를 보냅니다.
기본 권한은 `IsAuthenticatedOrReadOnly` (조회는 공개, 쓰기는 로그인 필요) 이며, 필요 시 뷰별로 `permission_classes` 를 지정합니다.

## 구조

```text
backend/
├── config/            # settings, urls, Scalar 문서 템플릿
└── apps/
    ├── accounts/      # 회원(근로자/사업주), JWT 인증, 평판
    ├── jobs/          # 일용직 구인·구직, 신청/승인, 일자리 지도
    ├── community/     # 지역 커뮤니티, 동행 모집, 후기
    ├── assistant/     # AI 행정·생활 지원 챗봇
    └── translation/   # 다국어 번역, 채팅 번역
```

## 협업 규칙

- 새 API 는 `apps/<앱>/urls.py` 를 만들고 `config/urls.py` 에 `api/<앱>/` 로 include 합니다.
- 뷰/시리얼라이저에 docstring 을 적으면 Scalar 문서에 설명으로 노출됩니다.
- 모델 변경 시 `makemigrations` 로 생성된 마이그레이션 파일을 함께 커밋합니다.
- 패키지 추가 시 `pip freeze > requirements.txt` 로 갱신 후 커밋합니다.
- `.env` 는 커밋하지 않습니다 (`.env.example` 만 관리).
- 사용자 모델은 `accounts.User` (`AUTH_USER_MODEL`) 를 사용합니다.
- 테스트: `python manage.py test` (PR 전에 통과 확인)
- 브랜치/커밋/PR 규칙은 루트 [README](../README.md) 와 [CONTRIBUTING](../.github/CONTRIBUTING.md) 참고.
