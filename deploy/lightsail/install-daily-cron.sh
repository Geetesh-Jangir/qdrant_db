#!/usr/bin/env bash
# Install news ingest crons on UTC Lightsail clock (no CRON_TZ on stock Ubuntu cron).
#   07:30 UTC = 13:00 IST (1:00 PM)  — news-daily-noon
#   11:40 UTC = 17:10 IST (5:10 PM)  — news-daily-evening
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
SCRIPT="${NEWS_RAG_DIR}/deploy/lightsail/run-daily-pipeline.sh"
MARK_NOON="# news-daily-noon"
MARK_EVENING="# news-daily-evening"

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
LINE_NOON="30 7 * * * /bin/bash ${SCRIPT} >> ${CRON_LOG} 2>&1 ${MARK_NOON}"
LINE_EVENING="40 11 * * * /bin/bash ${SCRIPT} >> ${CRON_LOG} 2>&1 ${MARK_EVENING}"

CURRENT="$(crontab -u "${SERVICE_USER}" -l 2>/dev/null || true)"
FILTERED="$(printf '%s\n' "${CURRENT}" \
  | grep -v "${MARK_NOON}" \
  | grep -v "${MARK_EVENING}" \
  | grep -v 'run-daily-pipeline.sh' \
  || true)"
TMP="$(mktemp)"
printf '%s\n%s\n%s\n' "${FILTERED}" "${LINE_NOON}" "${LINE_EVENING}" | sed '/^$/d' > "${TMP}"

if ! crontab -u "${SERVICE_USER}" "${TMP}"; then
  echo "!! crontab rejected this file:"
  cat -A "${TMP}"
  rm -f "${TMP}"
  exit 1
fi
rm -f "${TMP}"

echo "==> News crons for ${SERVICE_USER}:"
echo "    07:30 UTC = 13:00 IST (1:00 PM)  ${MARK_NOON}"
echo "    11:40 UTC = 17:10 IST (5:10 PM) ${MARK_EVENING}"
crontab -u "${SERVICE_USER}" -l