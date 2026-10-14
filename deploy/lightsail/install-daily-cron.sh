#!/usr/bin/env bash
# Install daily news cron at 00:00, 08:00, and 16:00 IST.
# Lightsail clocks are UTC, and Ubuntu cron rejects CRON_TZ, so the hours below are UTC.
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
SCRIPT="${NEWS_RAG_DIR}/deploy/lightsail/run-daily-pipeline.sh"

if [[ ! -f "${SCRIPT}" ]]; then
  echo "!! Missing ${SCRIPT}"
  exit 1
fi
chmod +x "${SCRIPT}"
mkdir -p "${NEWS_RAG_DIR}/data/news_runs_daily/cron"
if id "${SERVICE_USER}" &>/dev/null; then
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${NEWS_RAG_DIR}/data/news_runs_daily" || true
fi

TMP="$(mktemp)"
CRON_LOG="${NEWS_RAG_DIR}/data/news_runs_daily/cron/cron.log"
cat > "${TMP}" <<EOF
30 18 * * * ${SCRIPT} >> ${CRON_LOG} 2>&1
30 2 * * * ${SCRIPT} >> ${CRON_LOG} 2>&1
30 10 * * * ${SCRIPT} >> ${CRON_LOG} 2>&1
EOF

if ! crontab -u "${SERVICE_USER}" "${TMP}"; then
  echo "!! crontab rejected this file:"
  cat -A "${TMP}"
  rm -f "${TMP}"
  exit 1
fi
rm -f "${TMP}"

echo "==> Daily cron for ${SERVICE_USER}: 18:30, 02:30, 10:30 UTC (= 00:00, 08:00, 16:00 IST)"
crontab -u "${SERVICE_USER}" -l
