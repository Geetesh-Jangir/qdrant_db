#!/usr/bin/env bash
# Run historical news backfill on the server (reads .env in NEWS_RAG_DIR).
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
cd "${NEWS_RAG_DIR}"

if [[ -f "${NEWS_RAG_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${NEWS_RAG_DIR}/.env"
  set +a
fi

export PYTHONPATH="${NEWS_RAG_DIR}"
export NEWS_CORPUS_MODE="${NEWS_CORPUS_MODE:-true}"
export RETENTION_DAYS="${RETENTION_DAYS:-0}"
export FRESH_START_EACH_RUN="${FRESH_START_EACH_RUN:-false}"

VENV_PY="${NEWS_RAG_DIR}/.venv/bin/python"
if [[ ! -x "${VENV_PY}" ]]; then
  VENV_PY="$(command -v python3)"
fi

echo "==> backfill_days BACKFILL_START=${BACKFILL_START:-?} BACKFILL_END=${BACKFILL_END:-?}"
exec "${VENV_PY}" -m news_pipeline.backfill_days
