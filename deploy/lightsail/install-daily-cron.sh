#!/usr/bin/env bash
# Install daily news cron at midnight, 08:00, and 16:00 IST. Safe to rerun.
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
SCRIPT="${NEWS_RAG_DIR}/deploy/lightsail/run-daily-pipeline.sh"
MARKER="run-daily-pipeline.sh"
LINES=(
  "0 0 * * * ${SCRIPT}"
  "0 8 * * * ${SCRIPT}"
  "0 16 * * * ${SCRIPT}"
)

if [[ ! -f "${SCRIPT}" ]]; then
  echo "!! Missing ${SCRIPT}"
  exit 1
fi
chmod +x "${SCRIPT}"
mkdir -p "${NEWS_RAG_DIR}/data/news_runs_daily/cron"
if id "${SERVICE_USER}" &>/dev/null; then
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${NEWS_RAG_DIR}/data/news_runs_daily" || true
fi

EXISTING="$(crontab -u "${SERVICE_USER}" -l 2>/dev/null || true)"
FILTERED="$(printf '%s\n' "${EXISTING}" | grep -v "${MARKER}" | grep -v '^CRON_TZ=' || true)"

{
  echo "CRON_TZ=Asia/Kolkata"
  if [[ -n "${FILTERED}" ]]; then
    printf '%s\n' "${FILTERED}"
  fi
  printf '%s\n' "${LINES[@]}"
} | crontab -u "${SERVICE_USER}" -

echo "==> Daily cron for ${SERVICE_USER}: 00:00, 08:00, 16:00 Asia/Kolkata -> ${SCRIPT}"
crontab -u "${SERVICE_USER}" -l
