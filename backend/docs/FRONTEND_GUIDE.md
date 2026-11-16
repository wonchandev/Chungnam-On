# 프론트엔드 개발자를 위한 백엔드 가이드

React 프론트 팀원에게 전달하는 문서입니다. 상세 스키마는 **/docs (Scalar)** 를 기준으로 합니다.

## 1. 접속 정보
- 로컬 실행: [backend/README.md](../README.md) 의 "시작하기"
- API 문서(Scalar): `http://127.0.0.1:8000/docs` — 모든 엔드포인트의 요청/응답 스키마
- 모든 API 는 `/api/` 아래
- `backend/.env` 의 `CORS_ALLOWED_ORIGINS` 에 프론트 개발 서버 주소가 들어 있어야 합니다 (기본 `localhost:3000`, `5173`)

## 2. 인증 (JWT)
- `POST /api/auth/login/` → `access`(30분), `refresh`(7일)
- 요청 헤더: `Authorization: Bearer <access>`
- 401 이 오면 `POST /api/auth/refresh/` 로 재발급. **refresh 도 새로 바뀌므로 응답의 새 refresh 로 교체 저장**
- 로그아웃: `POST /api/auth/logout/` `{refresh}`
- 회원가입: `role` 은 `worker` | `employer`. employer 는 `company`(상호·사업자번호 등) 필수
- 이메일/전화 인증: `POST /api/auth/verify/request/` → `verify/confirm/` (개발 환경은 응답의 `dev_code` 사용), 비밀번호 찾기: `POST /api/auth/password-reset/request/` → `confirm/`, 회원 탈퇴: `POST /api/auth/withdraw/`
- 소셜 로그인(카카오/구글): `POST /api/auth/social/{provider}/` `{access_token}` (프론트에서 받은 provider 토큰 전달)

## 3. 공통 규칙
- **에러 형식**: 항상 `{code, message, detail}`. 폼 검증 에러는 `detail` 에 필드별로. 다국어 UI 는 `message` 대신 `code` 로 분기 권장
- **언어**: `Accept-Language: th` 헤더 → 공고 제목/설명, 행정 가이드, 커뮤니티 글, 표현집 등이 해당 언어로 내려옴. 헤더가 없으면 로그인 사용자의 `preferred_language`
- **지원 언어**: `ko, en, vi, th, zh, uz, km, ne, id, mn` (`GET /api/languages/`)
- **목록 응답**: `{count, next, previous, results}` (`?page=`)
- **날짜/시간**: `YYYY-MM-DD`, `HH:MM` / **금액**: 원 단위 정수
- **이미지 업로드**: `multipart/form-data`

## 4. 화면별 API

| 화면 | API |
|---|---|
| 홈 | 상단 배너 `GET /api/jobs/ticker/`, 긴급 채용 `GET /api/jobs/urgent/`, 나에게 딱 맞는 일자리 `GET /api/jobs/recommended/`, 별 아이콘 `POST/DELETE /api/jobs/{id}/bookmark/` |
| 구인구직 | `GET /api/jobs/popular-categories/`, `GET /api/categories/`, 검색 `?q=`, 인기 검색어 `GET /api/jobs/popular-searches/`, 관심 공고 `GET /api/jobs/bookmarks/`, 최근 본 공고 `GET /api/jobs/recent/`, 인력사무소 탭 `GET /api/agencies/`, 내 구직활동 `GET /api/applications/mine/` |
| 지도 | `GET /api/jobs/map/clusters/?zoom=&sw_lat=&sw_lng=&ne_lat=&ne_lng=`(숫자 버블), `GET /api/jobs/map/`(마커), `GET /api/jobs/nearby/?lat=&lng=&radius=`, 목록보기 `GET /api/jobs/?bbox=swLat,swLng,neLat,neLng`, 지역 검색 `GET /api/regions/search/?q=` |
| 공고 상세 | `GET /api/jobs/{id}/`, 지원 `POST /api/jobs/{id}/apply/`(응답의 `chat_room_id` 로 문의 채팅방 바로 이동), 문의 `POST /api/chat/rooms/` `{job_id}` |
| 사업주 | 공고 `POST /api/jobs/`, 복사 `POST /api/jobs/{id}/duplicate/`, 지원자 `GET /api/jobs/{id}/applications/`, 승인/거절 `PATCH /api/applications/{id}/`, 출근 확인 `POST /api/applications/{id}/check-in/`, 근무 완료 `POST /api/applications/{id}/complete/` |
| 다국어 소통 | 최근 대화 `GET /api/chat/rooms/`, 언어 교육 `GET /api/courses/` + `POST /api/courses/{id}/enroll/`, 음성 번역 `POST /api/translate/voice/`, 사진 번역 `POST /api/translate/image/`, 자주 쓰는 표현 `GET /api/phrases/` |
| 채팅방 | 이력 `GET /api/chat/rooms/{id}/messages/`, 추천 단어 `GET /api/chat/quick-replies/`, 번역 언어 `PATCH .../translation/`, 이미지 첨부 `POST .../messages/`(multipart), 전화 연결 `GET .../call/`, 나가기 `DELETE /api/chat/rooms/{id}/` |
| 행정관리 | `GET /api/admin-info/dashboard/ guides/ frequent/ popular/`, 민원 `POST/GET /api/admin-info/complaints/`, AI 챗봇 `POST /api/assistant/chat/`, 서류 초안 `POST /api/assistant/documents/` |
| 커뮤니티 | `GET/POST /api/community/posts/`, 댓글/좋아요, 동행 모집 `GET/POST /api/community/companions/` + `join/` |
| 알림(🔔) | `GET /api/notifications/`, `GET /api/notifications/unread-count/`, `POST /api/notifications/read-all/` |
| 마이 | `GET /api/me/summary/`, 사장님 온도 `GET /api/users/{id}/reputation/`, 근로자 이력 `GET/PUT /api/me/worker-profile/`, 설정(언어·알림) `PATCH /api/auth/me/`, 신고 `POST /api/reports/`, 차단 `POST/DELETE /api/blocks/{user_id}/` |

- 지도 하단 필터/퀵필터는 공고 목록과 **같은 파라미터**: `category, urgent, period, weekday, beginner_ok, with_friend, lunch_provided, local_preferred, night_shift, region, min_pay ...` (전체는 /docs)
- 업종 코드: `manufacturing, construction, agriculture, logistics, retail, safety, food, etc`
- 지역 코드: 천안 `44130`, 아산 `44200`, 당진 `44270` … (`GET /api/regions/`)

### 사진·음성 번역 응답
- **사진** `POST /api/translate/image/` (multipart `image`, `target`, `source`=auto 기본): 기존 `detected_text`·`translated_text`(전체 문장)에 더해 글자 영역별 결과를 줍니다.
  ```json
  {"detected_text": "...", "source": "auto", "target": "vi", "translated_text": "...",
   "image_width": 800, "image_height": 600,
   "regions": [{"text": "안전모 착용", "translated_text": "...", "language": "ko",
                "box": {"x": 0, "y": 0, "width": 300, "height": 50},
                "vertices": [{"x": 0, "y": 0}, {"x": 300, "y": 0}, {"x": 300, "y": 50}, {"x": 0, "y": 50}]}]}
  ```
  좌표는 업로드한 원본 이미지의 픽셀 기준입니다. 화면에 띄운 크기 ÷ `image_width`(`image_height`) 비율로 곱해 오버레이하세요. 기울어진 글자는 `vertices`(시계 방향 4점)를 쓰면 됩니다. 영역은 문단 단위이며 최대 100개입니다.
- **음성** `POST /api/translate/voice/` (multipart `audio`, `source`, `target`): webm/ogg/m4a/mp3/wav 등 대부분 형식을 서버가 변환하므로 `encoding`은 보낼 필요가 없습니다. 기본 **5분·25MB**까지 가능하고, 응답에 `duration_seconds`(초)가 추가됩니다. 너무 길면 413 `audio_too_long`, 해석할 수 없는 파일은 400 `unsupported_audio`입니다.

### 음성 합성과 실시간 번역

- `POST /api/translate/tts/`에 `{"text":"Wear a hard hat.","language":"en"}`를 보냅니다. 지원 언어는 `ko`, `en`, `vi`, `th`, `zh`, `id`이고 `text`는 UTF-8 5,000바이트까지입니다. 응답 `audio/mpeg`를 Blob으로 읽어 재생할 수 있습니다.
- 실시간 음성은 `ws://127.0.0.1:8000/ws/translate/voice/?token=<access>`로 접속합니다. `{"type":"start","source":"ko","target":"en"}`을 보내고 `ready`를 받은 다음, 16kHz 모노 PCM16 little-endian을 WAV 헤더 없이 바이너리 프레임으로 보냅니다. `ready`의 `max_frame_bytes`는 16,000, `max_audio_seconds`는 280입니다. 프레임을 녹음 속도에 맞춰 전송합니다.
- `transcript`에는 `segment`, `text`, `is_final`이 있습니다. `is_final=false`는 인식 중 표시용이고, 확정 문장은 동일 `segment`의 `translation` 이벤트로 `translated_text`가 업데이트됩니다.
- Claude가 번역한 이벤트에는 보정한 원문인 `corrected_text`가 추가됩니다. `text`에는 Google이 인식한 원문이 들어갑니다. 앞 문장의 번역을 기다리는 동안에도 새 자막이 도착할 수 있으므로 `segment`로 연결해 표시합니다.
- 녹음이 끝나면 `{"type":"stop"}`을 보내고 남은 번역과 `complete`를 기다립니다. `error` 이벤트의 `code`로 실패를 표시할 수 있고, `segment`가 있는 오류는 해당 문장의 번역 실패입니다.

## 5. 채팅 (WebSocket)
- 연결: `ws://127.0.0.1:8000/ws/chat/{room_id}/?token=<access>`
- 보내기: `{"type":"message","text":"..."}` | `{"type":"read"}`
- 받기: `message`(원문 + `translations: {언어: 번역문}`), `read`, `presence`(온라인 여부)
- 번역 표시: 메시지의 `source_lang`은 감지한 발신 언어입니다. `translations`에서 내 언어 키를 골라 표시하고, 해당 키가 없으면 원문을 표시합니다.
- 방 생성/이력/이미지 첨부는 REST, 실시간 텍스트 송수신은 WebSocket. WebSocket 이 안 될 때는 `POST .../messages/` 로도 전송 가능

## 6. 참고 / 제약
- **번역**: 공고 등록·수정 응답은 번역 완료 전에 돌아옵니다. 번역이 준비될 때까지 공고 API는 원문을 반환합니다. 개발용 Echo 엔진에서는 `[th] 원문` 형태로 표시합니다. 음성/사진 번역에는 Google 키가 필요합니다.
- **AI 챗봇 응답 추가 필드**(`done` 이벤트/JSON): `sources[{id,title,url}]` 출처 표기, `suggestions` 후속 질문 칩, `title` 대화 제목, `pii_masked`(여권·등록번호가 가려졌다는 안내용). 답변 👍/👎·신고는 `POST /api/assistant/messages/{message_id}/feedback/` `{rating:"up"|"down", reason, report}`, 대화 내보내기 `GET /api/assistant/conversations/{id}/export/`. 한도 초과는 429 `assistant_rate_limited`. 챗봇이 "지원할까요?"라고 되물으면 사용자 답변을 그대로 다시 보내면 됩니다
- **AI 챗봇**: `OPENAI_API_KEY` 가 없으면 행정 가이드를 검색해 요약해 주는 간이 답변으로 동작합니다
- **좌표**: 공고 등록 시 `lat`, `lng` 는 프론트(지도 SDK)가 구해서 보내야 합니다 (서버에 주소→좌표 변환 없음)
- **행정 가이드**: 콘텐츠는 `/admin/` 에서 등록해야 목록이 채워집니다
- **푸시 알림**: 서버는 알림 DB 저장/조회만 제공합니다 (FCM 등 푸시 발송은 미구현, 폴링 또는 unread-count 사용)
- 디자인상 "일 300,000만원" 은 "일 30만원" 오타로 보여 확인이 필요합니다

## 7. 요청하고 싶은 것
- 필요한 API 가 없거나 응답 필드가 부족하면 **Issue 로 등록**해 주세요
