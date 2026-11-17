#!/usr/bin/env bash
# Install news ingest crons on UTC Lightsail clock (no CRON_TZ on stock Ubuntu cron).
#   02:30 UTC = 08:00 IST — news-daily-morning
#   11:30 UTC = 17:00 IST (5:00 PM) — news-daily-evening
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
SCRIPT="${NEWS_RAG_DIR}/deploy/lightsail/run-daily-pipeline.sh"
MARK_MORNING="# news-daily-morning"
MARK_EVENING="# news-daily-evening"
# Legacy markers (remove old crontab lines from previous schedules)
MARK_NOON="# news-daily-noon"

if [[ ! -f "${SCRIPT}" ]]; then
  echo "!! Missing ${SCRIPT}"
  exit 1
fi
chmod +x "${SCRIPT}"
mkdir -p "${NEWS_RAG_DIR}/data/news_runs_daily/cron"
if id "${SERVICE_USER}" &>/dev/null; then
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${NEWS_RAG_DIR}/data/news_runs_daily" || true
fi

CRON_LOG="${NEWS_RAG_DIR}/data/news_runs_daily/cron/cron.log"
LINE_MORNING="30 2 * * * /bin/bash ${SCRIPT} >> ${CRON_LOG} 2>&1 ${MARK_MORNING}"
LINE_EVENING="30 11 * * * /bin/bash ${SCRIPT} >> ${CRON_LOG} 2>&1 ${MARK_EVENING}"

CURRENT="$(crontab -u "${SERVICE_USER}" -l 2>/dev/null || true)"
FILTERED="$(printf '%s\n' "${CURRENT}" \
  | grep -v "${MARK_MORNING}" \
  | grep -v "${MARK_EVENING}" \
  | grep -v "${MARK_NOON}" \
  | grep -v 'run-daily-pipeline.sh' \
  || true)"
TMP="$(mktemp)"
printf '%s\n%s\n%s\n' "${FILTERED}" "${LINE_MORNING}" "${LINE_EVENING}" | sed '/^$/d' > "${TMP}"

if ! crontab -u "${SERVICE_USER}" "${TMP}"; then
  echo "!! crontab rejected this file:"
  cat -A "${TMP}"
  rm -f "${TMP}"
  exit 1
fi
rm -f "${TMP}"

echo "==> News crons for ${SERVICE_USER}:"
echo "    02:30 UTC = 08:00 IST  ${MARK_MORNING}"
echo "    11:30 UTC = 17:00 IST  ${MARK_EVENING}"
crontab -u "${SERVICE_USER}" -l