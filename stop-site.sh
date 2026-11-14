#!/usr/bin/env bash
# Останавливает стенд на Linux (аналог stop-site.cmd для Windows).

set -euo pipefail

cd "$(dirname "$0")"

docker compose -f docker-compose.yml -f docker-compose.lan.yml down >/dev/null 2>&1 || true

echo "Стенд остановлен."
