# 1) 프론트 빌드
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# 2) Django(ASGI) + 빌드된 프론트를 한 서비스로 실행
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=web /web/dist ./frontend_dist
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput
CMD ["sh", "start.sh"]
