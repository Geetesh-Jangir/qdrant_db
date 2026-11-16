#!/usr/bin/env bash
# Run the insight orchestrator after the news ingest. Safe to start twice: the second exits while the lock is held.
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
LOCK="/tmp/insights-daily.lock"
LOG_DIR="${NEWS_RAG_DIR}/data/ai_insights/logs"
mkdir -p "${LOG_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${LOG_DIR}/daily_${STAMP}.log"

note() {
  logger -t insights-daily -- "$*" 2>/dev/null || true
  echo "$(date -u -Iseconds) $*" | tee -a "${LOG}"
}

exec 9>"${LOCK}"
if ! flock -n 9; then
  note "insights skipped: lock held"
  exit 0
fi

cd "${NEWS_RAG_DIR}"
if [[ -f "${NEWS_RAG_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${NEWS_RAG_DIR}/.env"
  set +a
fi
export PYTHONPATH="${NEWS_RAG_DIR}"
export PYTHONUNBUFFERED=1
VENV_PY="${NEWS_RAG_DIR}/.venv/bin/python"
note "insights start"
set +e
"${VENV_PY}" -m ai_insight.tools.run_daily >>"${LOG}" 2>&1
code=$?
set -e
note "insights exit=${code}"
exit "${code}"
