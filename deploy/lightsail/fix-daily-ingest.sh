#!/usr/bin/env bash
# One-shot on Lightsail after git pull: cron (8 AM + 5 PM IST), +x scripts, reinstall daily crons.
#   cd /opt/news-rag && sudo NEWS_RAG_DIR=/opt/news-rag bash deploy/lightsail/fix-daily-ingest.sh
set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
cd "${NEWS_RAG_DIR}"

chmod +x deploy/lightsail/*.sh

if [[ -f .env ]] && grep -qE '^HOLDINGS_LIMIT=(4[0-9]{2}|500)' .env 2>/dev/null; then
  echo "!! .env has HOLDINGS_LIMIT>250 — daily cron caps at 250 anyway (NEWS_PIPELINE_DAILY=1)."
  echo "   Remove or lower HOLDINGS_LIMIT=250 in .env for manual runs."
fi

NEWS_RAG_DIR="${NEWS_RAG_DIR}" bash deploy/lightsail/install-daily-cron.sh

echo ""
echo "==> Expected crontab (ubuntu):"
echo "    30 2 * * *  -> 08:00 IST  # news-daily-morning"
echo "    30 11 * * * -> 17:00 IST  # news-daily-evening"
crontab -u ubuntu -l 2>/dev/null | grep run-daily-pipeline || echo "!! no cron lines — check install-daily-cron.sh output"