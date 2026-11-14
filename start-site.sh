#!/usr/bin/env bash
# Запуск стенда на Linux (включая ARM) — аналог start-site.cmd для Windows.
# Останавливать: ./stop-site.sh

set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker не найден — устанавливаю…"
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh
    if command -v systemctl >/dev/null 2>&1; then
        systemctl enable --now docker >/dev/null 2>&1 || true
    fi
fi

ARCH="$(uname -m)"
case "$ARCH" in
    x86_64) DOCKER_ARCH="amd64" ;;
    aarch64|arm64) DOCKER_ARCH="arm64" ;;
    *) echo "Неподдерживаемая архитектура: $ARCH"; exit 1 ;;
esac

if ! docker image inspect 5-medvedey-backend:latest >/dev/null 2>&1; then
    ASSET="5-medvedey-images-linux-${DOCKER_ARCH}.tar.gz"
    TAR="dist/${ASSET}"
    mkdir -p dist
    if [ ! -f "$TAR" ]; then
        echo "Скачиваю готовые образы из GitHub Releases…"
        curl -fL --retry 3 -o "$TAR" "https://github.com/mopchiktopchik2-cell/5-medvedey/releases/download/images/${ASSET}"
    fi
    docker load -i "$TAR"
fi

if [ ! -f .env ]; then
    cp .env.example .env
fi
if ! grep -q '^SECRET_KEY=.' .env; then
    SECRET="$(head -c 32 /dev/urandom | base64 -w 0)"
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" .env
fi

docker compose -f docker-compose.yml -f docker-compose.lan.yml up -d

BACKEND_CID="$(docker compose -f docker-compose.yml -f docker-compose.lan.yml ps -q backend)"
OK=0
for i in $(seq 1 60); do
    STATUS="$(docker inspect -f '{{.State.Health.Status}}' "$BACKEND_CID" 2>/dev/null || echo unknown)"
    if [ "$STATUS" = "healthy" ]; then
        OK=1
        break
    fi
    sleep 2
done
if [ "$OK" -ne 1 ]; then
    echo "Сервис не готов. Логи: docker compose -f docker-compose.yml -f docker-compose.lan.yml logs backend"
    exit 1
fi

IP="$(hostname -I | awk '{print $1}')"
if [ -n "$IP" ]; then
    echo ""
    echo "Сайт: http://${IP}:8080"
else
    echo "Сайт: http://localhost:8080"
fi
