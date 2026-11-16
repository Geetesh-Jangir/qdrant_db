#!/usr/bin/env bash
# Install the insights cron at 17:30 IST (12:00 UTC). Idempotent: only this marked line is replaced.
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
SCRIPT="${NEWS_RAG_DIR}/scripts/run_insights_daily.sh"
MARK="# insights-daily"

if [[ ! -f "${SCRIPT}" ]]; then
  echo "!! Missing ${SCRIPT}"
  exit 1
fi
chmod +x "${SCRIPT}"
mkdir -p "${NEWS_RAG_DIR}/data/ai_insights/logs"

CURRENT="$(crontab -u "${SERVICE_USER}" -l 2>/dev/null || true)"
FILTERED="$(printf '%s\n' "${CURRENT}" | grep -v "${MARK}" | grep -v 'run_insights_daily.sh' || true)"
LINE="0 12 * * * /bin/bash ${SCRIPT} ${MARK}"
TMP="$(mktemp)"
printf '%s\n%s\n' "${FILTERED}" "${LINE}" | sed '/^$/d' > "${TMP}"
crontab -u "${SERVICE_USER}" "${TMP}"
rm -f "${TMP}"
echo "==> Insights cron for ${SERVICE_USER}: 12:00 UTC (= 17:30 IST)"
crontab -u "${SERVICE_USER}" -l
