# 행정관리

`/administration`은 공유된 화면을 참고해 대시보드, 분야별 안내, 자주 찾는 정보, 최근 인기, 내 민원과 알림을 구성한다. 챗봇과 AI 서류 초안 API는 호출하지 않는다.

## 연결 API

| 화면 | API |
| --- | --- |
| 대시보드 통계 | `GET /api/admin-info/dashboard/` |
| 행정 안내 목록·검색·분야 | `GET /api/admin-info/guides/?category=&search=&page=` |
| 안내 상세·공식 출처 | `GET /api/admin-info/guides/{id}/` |
| 자주 찾는 정보 | `GET /api/admin-info/frequent/?limit=50` |
| 최근 인기 | `GET /api/admin-info/popular/?limit=50` |
| 내 민원 목록·처리 상태 필터 | `GET /api/admin-info/complaints/?status=&category=&page=` |
| 민원 접수·상세 | `POST /api/admin-info/complaints/`, `GET /api/admin-info/complaints/{id}/` |
| 알림 목록·안 읽은 수 | `GET /api/notifications/`, `GET /api/notifications/unread-count/` |
| 알림 읽음·모두 읽음 | `POST /api/notifications/{id}/read/`, `POST /api/notifications/read-all/` |

## 동작

- 가이드와 통계는 비회원도 조회할 수 있다. 민원과 알림은 공통 로그인 세션·토큰 재발급을 사용한다.
- 분야별 바로가기는 백엔드 category와 검색어로 안내 목록을 조회한다. 증명서 안내·신고 등 검색 결과가 없으면 빈 상태를 표시한다.
- 비자·증명서·보험의 기관 직접 접수·발급 기능은 없다. 안내 상세와 공식 출처로 연결하며 정부기관 신청 완료로 표시하지 않는다.
- 민원은 충남온 운영자에게 보내는 문의이며 정부기관 공식 민원 접수와 구분한다. 접수 후 상세를 열고, 목록에서 접수·처리중·답변 완료를 확인한다. 상태·답변은 사용자가 수정할 수 없다.
- 대시보드의 진행 중인 문의는 `received`와 `in_progress`를 조회해 최신 3건을 보여준다.
- 알림은 사용자가 읽음 처리를 할 수 있고, 민원 답변 알림에서 관련 문의 상세를 열 수 있다.
- 목록은 API 데이터를 사용한다. 데모·빈 응답을 임의의 신청 내역으로 채우지 않는다.
- `useAdminResource`는 요청 변경 시 이전 결과를 감추고, 중단된 요청이 새 필터의 결과를 덮어쓰지 않도록 처리한다.

## 확인

- `npm run build`, 변경된 행정관리 파일 대상 ESLint.
- 기존 프론트 API 테스트와 백엔드 `apps.assistant.tests`, `apps.assistant.tests_p1.ComplaintTest`, `apps.core.tests`.
- 실제 민원 답변·상태 변경은 Django 관리자에서 처리한다. 사용자 화면은 해당 API 응답을 표시한다.
