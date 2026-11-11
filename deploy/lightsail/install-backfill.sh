#!/usr/bin/env bash
# Install systemd unit for on-server historical backfill (optional; GitHub Actions is fine too).
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
  SUDO="sudo"
fi

if [[ ! -f "${NEWS_RAG_DIR}/news_pipeline/backfill_days.py" ]]; then
  echo "!! Clone repo to ${NEWS_RAG_DIR} first."
  exit 1
fi

chmod +x "${SCRIPT_DIR}/run-backfill.sh"
${SUDO} cp "${SCRIPT_DIR}/news-backfill.service" /etc/systemd/system/news-backfill.service
${SUDO} systemctl daemon-reload
${SUDO} systemctl enable news-backfill.service

echo "==> Installed news-backfill.service"
echo "    Set BACKFILL_START / BACKFILL_END in ${NEWS_RAG_DIR}/.env"
echo "    sudo systemctl start news-backfill.service"
echo "    journalctl -u news-backfill.service -f"
