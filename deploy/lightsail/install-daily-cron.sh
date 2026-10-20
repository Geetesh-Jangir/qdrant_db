#!/usr/bin/env bash
# Install daily news cron at 17:00 IST (5 PM) once per day.
# Lightsail clocks are UTC, and Ubuntu cron rejects CRON_TZ, so the line below is UTC.
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
30 11 * * * ${SCRIPT} >> ${CRON_LOG} 2>&1
EOF

if ! crontab -u "${SERVICE_USER}" "${TMP}"; then
  echo "!! crontab rejected this file:"
  cat -A "${TMP}"
  rm -f "${TMP}"
  exit 1
fi
rm -f "${TMP}"

echo "==> Daily cron for ${SERVICE_USER}: 11:30 UTC (= 17:00 IST / 5 PM)"
crontab -u "${SERVICE_USER}" -l
