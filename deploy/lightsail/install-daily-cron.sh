#!/usr/bin/env bash
# Install daily news cron at midnight, 08:00, and 16:00 IST. Safe to rerun.
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
SCRIPT="${NEWS_RAG_DIR}/deploy/lightsail/run-daily-pipeline.sh"
MARKER="run-daily-pipeline.sh"
# Ubuntu's cron rejects CRON_TZ (error: bad hour). Use local hours only when the
# instance clock is already India time; otherwise schedule the UTC equivalents.
TZ_NAME="$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo UTC)"
if [[ "${TZ_NAME}" == "Asia/Kolkata" || "${TZ_NAME}" == "Asia/Calcutta" ]]; then
  LINES=(
    "0 0 * * * ${SCRIPT}"
    "0 8 * * * ${SCRIPT}"
    "0 16 * * * ${SCRIPT}"
  )
  SCHEDULE_NOTE="00:00, 08:00, 16:00 ${TZ_NAME}"
else
  LINES=(
    "30 18 * * * ${SCRIPT}"
    "30 2 * * * ${SCRIPT}"
    "30 10 * * * ${SCRIPT}"
  )
  SCHEDULE_NOTE="18:30, 02:30, 10:30 UTC (= 00:00, 08:00, 16:00 IST); server timezone is ${TZ_NAME}"
fi

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
FILTERED="$(printf '%s\n' "${EXISTING}" | grep -v "${MARKER}" | grep -v '^CRON_TZ=' | grep -v '^[[:space:]]*$' || true)"

{
  if [[ -n "${FILTERED}" ]]; then
    printf '%s\n' "${FILTERED}"
  fi
  printf '%s\n' "${LINES[@]}"
} | crontab -u "${SERVICE_USER}" -

echo "==> Daily cron for ${SERVICE_USER}: ${SCHEDULE_NOTE}"
crontab -u "${SERVICE_USER}" -l
