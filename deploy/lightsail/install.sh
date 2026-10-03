#!/usr/bin/env bash
# Run ON a Lightsail Ubuntu instance (News RAG only — Option A).
#
# One-liner from your laptop (replace IP and key):
#   scp -r deploy/lightsail ubuntu@YOUR_LIGHTSAIL_IP:/tmp/news-rag-deploy
#   ssh ubuntu@YOUR_LIGHTSAIL_IP 'sudo bash /tmp/news-rag-deploy/install.sh'
#
# Or clone from GitHub on the server:
#   export NEWS_RAG_REPO=https://github.com/YOUR_ORG/YOUR_REPO.git
#   curl -fsSL .../install.sh | sudo -E bash

set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
NEWS_RAG_REPO="${NEWS_RAG_REPO:-}"
NEWS_RAG_BRANCH="${NEWS_RAG_BRANCH:-huge-corpus}"
RAG_PORT="${RAG_PORT:-8081}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> News RAG Lightsail install (same instance, port ${RAG_PORT})"

if ! command -v python3 >/dev/null || ! command -v nginx >/dev/null; then
  apt-get update -qq
  apt-get install -y python3 python3-venv python3-pip git nginx curl build-essential
fi

if [[ -n "${NEWS_RAG_REPO}" ]]; then
  if [[ ! -d "${NEWS_RAG_DIR}/.git" ]]; then
    mkdir -p "$(dirname "${NEWS_RAG_DIR}")"
    git clone --branch "${NEWS_RAG_BRANCH}" "${NEWS_RAG_REPO}" "${NEWS_RAG_DIR}"
  else
    cd "${NEWS_RAG_DIR}"
    git fetch origin
    git checkout "${NEWS_RAG_BRANCH}"
    git pull origin "${NEWS_RAG_BRANCH}"
  fi
elif [[ -f "${SCRIPT_DIR}/../../news_rag/app.py" ]]; then
  NEWS_RAG_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
  echo "==> Using existing repo at ${NEWS_RAG_DIR}"
else
  echo "Set NEWS_RAG_REPO or run from a cloned repo (see deploy/lightsail/DEPLOY.md)"
  exit 1
fi

cd "${NEWS_RAG_DIR}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -r news_rag/requirements.txt

export PYTHONPATH="${NEWS_RAG_DIR}"
python scripts/download_embedding_model.py

mkdir -p data/rag_query_logs data/embedding_models

if [[ ! -f .env ]]; then
  cp deploy/lightsail/.env.production.example .env
  echo ""
  echo "!! Created ${NEWS_RAG_DIR}/.env — edit QDRANT_* and LLM keys, then rerun this script:"
  echo "   nano ${NEWS_RAG_DIR}/.env"
  exit 0
fi

if grep -q 'YOUR_CLUSTER.cloud.qdrant.io' .env 2>/dev/null; then
  echo "Edit .env (QDRANT_URL, QDRANT_API_KEY, GEMINI_API_KEY), then rerun install.sh"
  exit 1
fi

# systemd unit with correct paths and port
UNIT=/etc/systemd/system/news-rag.service
sed -e "s|/opt/news-rag|${NEWS_RAG_DIR}|g" \
    -e "s|User=ubuntu|User=${SERVICE_USER}|g" \
    -e "s|Group=ubuntu|Group=${SERVICE_USER}|g" \
    -e "s|--port 8081|--port ${RAG_PORT}|g" \
    deploy/lightsail/news-rag.service > /tmp/news-rag.service
sudo cp /tmp/news-rag.service "${UNIT}"

sudo systemctl daemon-reload
sudo systemctl enable news-rag
sudo systemctl restart news-rag

sleep 2
if curl -sf "http://127.0.0.1:${RAG_PORT}/health" >/dev/null; then
  echo "==> OK: http://127.0.0.1:${RAG_PORT}/health"
else
  echo "==> Service started but health check failed. Logs:"
  sudo journalctl -u news-rag -n 40 --no-pager
  exit 1
fi

if [[ -f deploy/lightsail/nginx-rag-only.conf ]]; then
  cp deploy/lightsail/nginx-rag-only.conf /etc/nginx/sites-available/news-rag
  ln -sf /etc/nginx/sites-available/news-rag /etc/nginx/sites-enabled/news-rag
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl reload nginx
  echo "==> Nginx: public site -> http://YOUR_IP/ (proxies to port ${RAG_PORT})"
fi
echo "==> Do not open port ${RAG_PORT} in Lightsail firewall — use 80 only."
