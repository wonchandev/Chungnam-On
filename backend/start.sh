#!/bin/sh
# Railway 시작 스크립트: DB 준비 → 데모 데이터 → 서버 실행 (WebSocket 지원 daphne)
set -e
python manage.py migrate --noinput
python manage.py seed_demo || true
if [ -n "$OPENAI_API_KEY" ]; then python manage.py index_guides || true; fi
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
