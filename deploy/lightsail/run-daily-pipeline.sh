#!/usr/bin/env bash
# Daily news ingest on Lightsail. Rolling Google window (when:1d), not calendar after/before.
# Logs go under data/news_runs_daily/, separate from historical backfill in data/news_runs/.
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
LOCK="/tmp/news-pipeline.lock"
LOG_DIR="${NEWS_RAG_DIR}/data/news_runs_daily/cron"
mkdir -p "${LOG_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${LOG_DIR}/daily_${STAMP}.log"
RUNLOG="${LOG_DIR}/cron.log"

note() {
  local line
  line="$(date -u -Iseconds) $*"
  echo "${line}" >>"${RUNLOG}"
  echo "${line}" >>"${LOG}"
  logger -t news-daily -- "${line}" 2>/dev/null || true
}

exec 9>"${LOCK}"
if ! flock -n 9; then
  note "daily skipped: ${LOCK} already held"
  exit 0
fi

if pgrep -f '[p]ython.*-m news_pipeline' >/dev/null 2>&1; then
  note "daily skipped: news_pipeline or backfill_days already running"
  exit 0
fi

cd "${NEWS_RAG_DIR}"
if [[ -f "${NEWS_RAG_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${NEWS_RAG_DIR}/.env"
  set +a
fi

unset NEWS_DATE_RANGE || true
unset NEWS_RUN_SUBDIR || true

export PYTHONPATH="${NEWS_RAG_DIR}"
export PYTHONUNBUFFERED=1
export GOOGLE_NEWS_WHEN=1d
export NEWS_WINDOW_HOURS=24
export HOLDINGS_LIMIT=500
export SECTORS_LIMIT=30
export MACRO_NEWS_ENABLED=true
export NEWS_CORPUS_MODE=true
export RETENTION_DAYS=0
export FRESH_START_EACH_RUN=false
export FRESH_START_CLEAR_QDRANT=false
export RUN_SUMMARY_DIR=data/news_runs_daily

VENV_PY="${NEWS_RAG_DIR}/.venv/bin/python"
if [[ ! -x "${VENV_PY}" ]]; then
  note "daily failed: missing ${VENV_PY}"
  exit 1
fi

{
  echo "==> daily pipeline $(date -u -Iseconds)"
  echo "GOOGLE_NEWS_WHEN=${GOOGLE_NEWS_WHEN} NEWS_WINDOW_HOURS=${NEWS_WINDOW_HOURS}"
  echo "HOLDINGS_LIMIT=${HOLDINGS_LIMIT} SECTORS_LIMIT=${SECTORS_LIMIT} MACRO_NEWS_ENABLED=${MACRO_NEWS_ENABLED}"
  echo "RUN_SUMMARY_DIR=${RUN_SUMMARY_DIR} NEWS_DATE_RANGE=(unset)"
} >>"${LOG}" 2>&1

set +e
"${VENV_PY}" -m news_pipeline >>"${LOG}" 2>&1
code=$?
set -e

if [[ "${code}" -eq 0 ]]; then
  note "daily success exit=0 detail=${LOG}"
else
  note "daily failed exit=${code} detail=${LOG}"
fi
exit "${code}"
