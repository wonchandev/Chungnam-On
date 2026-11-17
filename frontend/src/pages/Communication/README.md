# 다국어 소통

`/communication`은 앞서 공유된 메인·채팅 화면을 참고해 구성한다. 디자인 원본을 그대로 사용한 화면이 아니라 기존 프론트의 색상·컴포넌트로 구성한 반응형 구현이다.

## API와 권한

- 공개: `languages/`, `courses/`, `phrases/` (한국어 검색·언어 선택).
- 로그인: `courses/{id}/enroll/` 신청·취소, `translate/text/`, `translate/voice/`, `translate/image/`, `translate/tts/`.
- 최근 대화: `chat/rooms/`, 채팅 상세·메시지·읽음·번역 언어·전화·나가기 API. 전화번호는 지원 승인 이후에만 백엔드가 제공한다.
- 채팅 수신은 `/ws/chat/{id}/`를 사용한다. 연결이 끊기면 화면을 보고 있는 동안 8초 간격으로 최신 메시지를 확인한다. 전송은 응답을 확인할 수 있는 REST를 사용한다. 이전 메시지는 커서 페이지네이션으로 조회한다.
- 실시간 통역은 `/ws/translate/voice/`에 start JSON, 16kHz 모노 PCM16-LE 바이너리, stop JSON을 보낸다. AudioWorklet에서 20ms 프레임으로 변환한다. 마이크는 사용자가 시작할 때만 요청하고 종료·화면 닫기·연결 오류 시 해제한다.

## 실행 조건

- 프론트 개발·미리보기 서버는 `/api`, `/media`, `/ws`를 백엔드로 전달한다. 운영에서도 WebSocket upgrade를 포함한 역방향 프록시가 필요하다.
- 다른 API 호스트를 쓰면 `VITE_API_BASE_URL`을 지정한다. WebSocket은 해당 API 호스트의 `/ws/`로 연결된다.
- 마이크는 localhost 또는 HTTPS와 브라우저 권한이 필요하다.
- 실제 번역·음성 인식·OCR·TTS는 백엔드 Google API 설정이 필요하다. 프론트에 API 키를 넣지 않는다. 키가 없는 서버의 개발용 EchoTranslator는 `[언어] 원문`을 반환하며 실제 번역 결과가 아니다.
- 음성은 녹음 또는 파일 업로드(5분·25MB), 사진은 파일 업로드(10MB)를 지원한다. 번역문 음성은 서버 TTS가 지원하는 언어에서 재생한다.
- 빈 데이터에 가짜 대화나 교육을 넣지 않는다. 로컬 `seed_demo` 계정에 채팅방이 없다면 최근 대화가 비어 있는 것이 정상이다.

## 확인

- `npm test`: JSON·multipart·TTS 응답, 토큰 갱신, PCM 프레임 규격.
- `npm run build`: 빌드.
- 실제 마이크 통역·사진 번역·TTS 품질은 유효한 외부 API 설정과 실제 기기로 별도 확인해야 한다.
