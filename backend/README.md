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
| `REDIS_URL` | 채팅 채널 레이어·캐시(온라인 상태) 공유용. **운영 필수**, 로컬은 비워도 됨 | 메모리 |
| `GOOGLE_TRANSLATE_API_KEY` | Google Cloud Translation API 키. 없으면 개발용 echo 번역(`[th] 원문`) | 빈 값 |
| `GOOGLE_TTS_API_KEY` | Google Cloud Text-to-Speech 전용 키. 비우면 번역용 Google 키 사용 | 빈 값 |
| `GOOGLE_TTS_USE_ADC` | 음성 합성 요청에 Google Application Default Credentials 사용 | `False` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | AI 챗봇(OpenAI). 키가 없으면 행정 가이드 검색 기반 간이 답변 | 빈 값 / `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` / `ASSISTANT_DAILY_LIMIT` | 가이드 임베딩 모델 / 사용자별 하루 챗봇 질문 한도 | `text-embedding-3-small` / `50` |
| `EMAIL_BACKEND` | 인증번호·비밀번호 재설정 메일 (기본 콘솔 출력) | console |
| `TRANSLATION_BACKEND` | (선택) 번역 엔진 클래스 경로. 키가 있으면 자동으로 `GoogleTranslator` | 자동 |
| `TRANSLATION_CACHE_TTL_DAYS` | 번역 캐시 재사용 기간(일). `0`은 캐시 사용 중지 | 30 |

## API 개요

전체 목록·요청/응답 스키마는 **/docs (Scalar)** 에서 확인하세요. 인증이 필요한 API 는 `Authorization: Bearer <access>`.
기본 권한은 `IsAuthenticatedOrReadOnly`, 뷰별로 사업주/근로자 권한을 따로 지정합니다.
에러 응답은 항상 `{"code": "...", "message": "...", "detail": ...}` 형식입니다.
언어는 `Accept-Language` 헤더 → 로그인 사용자의 `preferred_language` → `ko` 순서로 결정됩니다.

| 영역 | 엔드포인트 |
| --- | --- |
| 인증 | `POST /api/auth/register/ login/ refresh/ logout/ withdraw/` · `PATCH /api/auth/password/` · `GET/PATCH /api/auth/me/` · `POST /api/auth/verify/request/ verify/confirm/`(이메일·전화 인증) · `POST /api/auth/password-reset/request/ confirm/` · `POST /api/auth/social/{kakao\|google}/` |
| 마이 | `GET /api/me/summary/` · `GET/PUT /api/me/worker-profile/`(이력) · 설정은 `PATCH /api/auth/me/` (`preferred_language`, `notifications_enabled`) |
| 공고 | `GET/POST /api/jobs/` · `GET/PATCH/DELETE /api/jobs/{id}/` · `POST /api/jobs/{id}/close/ duplicate/` · `GET /api/jobs/mine/ urgent/ popular-categories/ recommended/ ticker/ recent/ popular-searches/` · `GET /api/categories/` |
| 지원 | `POST /api/jobs/{id}/apply/`(문의 채팅방 자동 생성) · `GET /api/applications/mine/` · `DELETE /api/applications/{id}/` · `GET /api/jobs/{id}/applications/` · `PATCH /api/applications/{id}/`(승인/거절) · `POST /api/applications/{id}/check-in/ complete/` |
| 관심·인력사무소 | `POST/DELETE /api/jobs/{id}/bookmark/` · `GET /api/jobs/bookmarks/` · `GET /api/agencies/ agencies/{id}/` |
| 평판 | `POST /api/jobs/{id}/reviews/`(근무 완료 후) · `GET /api/users/{id}/reputation/` |
| 지도 | `GET /api/jobs/map/` · `/api/jobs/map/clusters/` · `/api/jobs/nearby/` · `GET /api/jobs/?bbox=` · `GET /api/regions/ regions/search/` |
| 채팅 | `GET/POST /api/chat/rooms/` · `GET/DELETE /api/chat/rooms/{id}/` · `GET/POST .../messages/`(이미지 첨부) · `POST .../read/` · `PATCH .../translation/` · `GET .../call/` · `GET /api/chat/quick-replies/` |
| 번역·언어 | `POST /api/translate/text/ voice/ image/ tts/` · `GET /api/languages/ phrases/` · `GET /api/courses/ courses/mine/` · `POST/DELETE /api/courses/{id}/enroll/` |
| 행정관리 | `GET /api/admin-info/dashboard/ guides/ guides/{id}/ frequent/ popular/` · `GET/POST /api/admin-info/complaints/` |
| AI 지원 | `POST /api/assistant/chat/`(SSE 스트리밍 지원) · `GET /api/assistant/conversations/` · `GET .../conversations/{id}/export/`(txt 내보내기) · `POST /api/assistant/messages/{id}/feedback/`(👍/👎·신고) · `GET /api/assistant/documents/templates/` · `POST /api/assistant/documents/` |
| 커뮤니티 | `GET/POST /api/community/posts/` · `.../posts/{id}/ like/ comments/` · `DELETE /api/community/comments/{id}/` · `GET/POST /api/community/companions/` · `.../companions/{id}/ join/ participants/` |
| 알림·안전 | `GET /api/notifications/ unread-count/` · `POST /api/notifications/read-all/ {id}/read/` · `GET/POST /api/reports/`(내 신고 목록·신고 접수) · `GET /api/blocks/` · `POST/DELETE /api/blocks/{user_id}/` |

공고 목록·지도·주변검색은 같은 필터를 씁니다:
`q, region, category, bbox, pay_type, min_pay, max_pay, period(one_day|short|mid|long), weekday, work_date, urgent, beginner_ok, with_friend, lunch_provided, local_preferred, night_shift, ordering(created_at|pay_amount|deadline|start_date)`

### WebSocket 채팅

`ws://<host>/ws/chat/<room_id>/?token=<access>` (브라우저는 헤더를 못 붙이므로 쿼리로 JWT 전달)

- 보내기: `{"type":"message","text":"..."}` · `{"type":"read"}`
- 받기: `{"type":"message","message":{id,text,source_lang,translations{언어:번역문},...}}` · `{"type":"read",...}` · `{"type":"presence","user":id,"online":bool}`
- 방 생성은 REST(`POST /api/chat/rooms/`, 공고 문의 시 `job_id`), 이력은 REST 커서 페이지네이션.

### 번역 (Google Cloud Translation)

1. GCP 콘솔에서 **Cloud Translation API** 를 사용 설정하고 API 키를 발급합니다 (키는 해당 API 로만 제한 권장).
2. `.env` 에 `GOOGLE_TRANSLATE_API_KEY=...` 를 넣으면 공고 자동 번역, 채팅 번역, `/api/translate/text/` 가 모두 구글 번역을 사용합니다.
3. 같은 원문·언어쌍은 DB(`TranslationCache`)에 저장해 API 를 다시 호출하지 않습니다 (비용 절감). 번역 실패 시에도 공고 등록/메시지 전송은 성공하고 해당 언어 번역만 비어 있습니다.
4. 서비스 언어 코드 중 `zh` 는 구글의 `zh-CN` 으로 변환됩니다 (`GoogleTranslator.CODE_MAP`). 지원 언어는 `settings.SUPPORTED_LANGUAGES`.
5. 개발·테스트에서는 키 없이도 동작하며, 테스트는 외부 호출 없이 mock 으로 검증합니다.

번역 캐시는 유니코드 NFC와 줄바꿈을 정규화한 원문을 사용합니다. 번역 엔진·모델과 입력에 적용된 용어집 내용이 같고 기간 내인 결과를 재사용합니다. 기간이 지난 결과는 다음 요청 때 새 번역으로 갱신합니다.

텍스트 번역은 공급자 타임아웃에 `504 translation_timeout`, 일시적인 요청 제한에 `503 translation_rate_limited`, 일일·결제 한도 초과에 `503 translation_quota_exhausted`를 응답합니다. 공급자가 대기 시간을 주면 `Retry-After` 헤더에 포함합니다.

채팅의 `source_lang`은 실제 발신 텍스트의 감지 결과입니다. 감지에 실패하거나 텍스트가 없는 메시지에는 채팅 설정 언어를 사용합니다. 텍스트 번역 API에서는 `source: "auto"`로 자동 감지를 요청할 수 있습니다. 공고와 한국어 채팅에는 [현장 용어집](apps/translation/glossary.py)의 번역어를 적용합니다.

### 공고 번역 워커

공고 등록·복사·번역 대상 문구 수정은 원문을 저장하고 번역을 대기열에 추가합니다. 번역이 완료되기 전과 실패한 언어의 조회 응답은 원문을 표시합니다. 워커는 제목·설명·직무를 대상 언어별로 한 번에 번역 요청합니다.

마이그레이션을 적용한 뒤 백엔드 서버와 같은 데이터베이스를 사용하는 별도 프로세스에서 워커를 실행합니다.

```bash
python manage.py migrate
python manage.py translate_jobs
```

타임아웃, 일시적인 요청 제한, 공급자 장애는 기본 30·60·120초 간격으로 최대 3번 재시도합니다. 공급자가 `Retry-After`를 주면 안내한 시간 이상 대기합니다. 성공한 언어는 바로 조회할 수 있고 재시도에서도 유지합니다.

`python manage.py translate_jobs --once`는 현재 실행 가능한 작업을 처리하고 종료합니다. 한도나 공급자 설정을 바로잡은 뒤 `python manage.py translate_jobs --retry-failed --once`로 실패한 공고의 남은 번역을 다시 대기열에 등록하고 실행할 수 있습니다.

### AI 챗봇 / 음성·사진 번역
- 챗봇 고도화: 행정 가이드 9건이 마이그레이션으로 시드됩니다(내용은 일반 안내이므로 admin 에서 검수·보강). 키가 있으면 `python manage.py index_guides` 로 문단 단위 임베딩 색인을 만들고(admin 에서 가이드를 저장해도 자동 색인), 이후 질의는 번역 없이 의미 검색합니다. 챗봇은 공고 검색·지원 현황·지원/관심 등록(사용자 확인 후)·급여 계산 도구를 호출하며, 응답에 출처·후속 질문·대화 제목·개인정보 마스킹 여부가 포함됩니다. 하루 질문 한도 초과 시 429 `assistant_rate_limited`.

- 챗봇: `.env` 에 `OPENAI_API_KEY` 를 넣으면 OpenAI 모델이 행정 가이드(관리자 페이지에서 등록)를 근거로 답합니다. 키가 없으면 가이드 검색 결과를 요약해 보여주는 간이 모드로 동작합니다. 모델은 `OPENAI_MODEL` 로 변경합니다 (계정에서 사용 가능한 모델명으로).
- 번역을 OpenAI 로 바꾸려면 `TRANSLATION_BACKEND=apps.translation.backends.OpenAITranslator` (모델 `OPENAI_TRANSLATE_MODEL`). 기본은 Google 번역이며, 음성/사진 번역(STT/OCR)은 항상 Google 키가 필요합니다.
- 음성/사진 번역은 번역과 같은 `GOOGLE_TRANSLATE_API_KEY` 를 쓰며, GCP 에서 **Speech-to-Text API**, **Cloud Vision API** 도 사용 설정해야 합니다.
- 이메일 인증/비밀번호 재설정 메일은 기본적으로 콘솔에 출력됩니다. `DEBUG=True` 일 때는 응답에 `dev_code` 가 포함되어 프론트 개발 시 메일 없이 테스트할 수 있습니다. SMS 는 미연동(로그만).

### 번역 P2

- `python manage.py compare_translation_engines`는 Google과 OpenAI에 같은 한국어 현장 문장 4개를 보내 영어 번역, 참고 번역, 수치·용어 검사 결과와 응답 시간을 JSON으로 출력합니다. 키를 설정한 엔진을 비교하며 `--provider google` 또는 `--provider openai`로 한쪽만 실행할 수 있습니다.
- `python manage.py pretranslate_phrases --target en --target vi`는 현장 표현집과 채팅 빠른 답장의 번역 캐시를 미리 채웁니다. 언어 지정을 생략하면 지원하는 모든 대상 언어를 준비합니다. API 조회는 기존 번역 캐시에서 결과를 읽고, 만료 정책도 동일하게 적용됩니다.
- 채팅 원문은 그대로 저장합니다. 번역 요청에 쓰는 텍스트에서 `ㅇㅋ`, `ㄳ`, `ㅋㅋ`, `ASAP`, `THX` 등의 독립된 약어를 풀고, 이모지와 `:)` 같은 이모티콘을 번역문에 보존합니다.
- `POST /api/translate/tts/`는 `text`와 `language`를 받아 MP3 (`audio/mpeg`)를 반환합니다. Google 프로젝트에서 **Cloud Text-to-Speech API**를 사용 설정하고 키의 허용 API에 추가합니다. 별도 키는 `GOOGLE_TTS_API_KEY`에 넣을 수 있습니다. Google Application Default Credentials를 설정한 환경은 `GOOGLE_TTS_USE_ADC=True`로 합성 요청을 인증합니다. [Google 인증 설정](https://docs.cloud.google.com/text-to-speech/docs/authentication)
- `ws/translate/voice/`는 기존 JWT와 Speech-to-Text 키로 연결합니다. 마이크의 PCM 프레임을 보내면 인식 중 텍스트와 확정 문장별 번역을 받습니다. 자세한 메시지 형식은 [프론트엔드 API 가이드](docs/FRONTEND_GUIDE.md#음성-합성과-실시간-번역)를 참고하세요.
- `ANTHROPIC_API_KEY`를 설정하면 실시간 음성의 확정 문장과 같은 연결에서 인식한 직전 두 문장을 Claude에 보내 문맥 보정과 번역을 수행합니다. 응답 제한 시간은 확정 원문 길이에 따라 3~15초입니다. 키가 비어 있거나 호출에 실패하면 기본 번역 엔진을 사용합니다.

### 정기 작업

마감일/근무일이 지난 공고 자동 마감: `python manage.py close_expired_jobs` 를 cron 등으로 하루 1회 이상 실행.

## 구조

```text
backend/
├── config/            # settings, urls, Scalar 문서 템플릿
└── apps/
    ├── core/          # 공통: 지역(Region), 에러 포맷, 언어 결정, 알림·신고·차단
    ├── accounts/      # 회원(근로자/사업주·Company), JWT 인증, 평판(온도)
    ├── jobs/          # 공고, 지원/승인, 관심, 후기, 지도(마커·클러스터·주변)
    ├── chat/          # 채팅방/메시지, WebSocket, 메시지 자동 번역
    ├── translation/   # 번역 서비스(엔진 어댑터 + DB 캐시), 번역 API
    ├── assistant/     # 행정관리(대시보드·가이드·민원), AI 챗봇(RAG), 서류 초안
    └── community/     # 지역 커뮤니티(글·댓글·좋아요), 동행 모집
```

## 협업 규칙

- 새 API 는 `apps/<앱>/urls.py` 를 만들고 `config/urls.py` 에 `api/<앱>/` 로 include 합니다.
- 뷰/시리얼라이저에 docstring 을 적으면 Scalar 문서에 설명으로 노출됩니다.
- 모델 변경 시 `makemigrations` 로 생성된 마이그레이션 파일을 함께 커밋합니다.
- 패키지 추가 시 `pip freeze > requirements.txt` 로 갱신 후 커밋합니다.
- `.env` 는 커밋하지 않습니다 (`.env.example` 만 관리).
- 사용자 모델은 `accounts.User` (`AUTH_USER_MODEL`) 를 사용합니다.
- 테스트: `python manage.py test` (PR 전에 통과 확인). 공용 헬퍼는 `apps/core/testing.py`.
- 지역(시군)·업종은 마이그레이션으로 시드되므로 `migrate` 만 하면 준비됩니다.
- 진행 현황/설계 메모: [docs/API_TODO.md](docs/API_TODO.md)
- 브랜치/커밋/PR 규칙은 루트 [README](../README.md) 와 [CONTRIBUTING](../.github/CONTRIBUTING.md) 참고.
