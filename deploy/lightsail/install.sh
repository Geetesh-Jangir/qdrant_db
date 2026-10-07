#!/usr/bin/env bash
# Run ON a Lightsail Ubuntu instance (News RAG only — Option A).
# Instance example: ask-question
#
#   cd /opt/news-rag && sudo NEWS_RAG_DIR=/opt/news-rag bash deploy/lightsail/install.sh

set -euo pipefail

NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"
NEWS_RAG_REPO="${NEWS_RAG_REPO:-https://github.com/Geetesh-Jangir/qdrant_db.git}"
NEWS_RAG_BRANCH="${NEWS_RAG_BRANCH:-ask-a-question}"
RAG_PORT="${RAG_PORT:-8081}"
SERVICE_USER="${SERVICE_USER:-ubuntu}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
  SUDO="sudo"
fi

echo "==> News RAG Lightsail install (port ${RAG_PORT}, branch ${NEWS_RAG_BRANCH})"

if ! command -v python3 >/dev/null || ! command -v nginx >/dev/null; then
  ${SUDO} apt-get update -qq
  ${SUDO} DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 python3-venv python3-pip git nginx curl build-essential python-is-python3
fi

if [[ ! -d "${NEWS_RAG_DIR}/.git" ]]; then
  ${SUDO} mkdir -p "$(dirname "${NEWS_RAG_DIR}")"
  if [[ -d "${NEWS_RAG_DIR}" ]]; then
    echo "!! ${NEWS_RAG_DIR} exists but is not a git repo. Remove or set NEWS_RAG_DIR."
    exit 1
  fi
  echo "==> Cloning ${NEWS_RAG_REPO} (branch ${NEWS_RAG_BRANCH})"
  ${SUDO} git clone --depth 1 --branch "${NEWS_RAG_BRANCH}" "${NEWS_RAG_REPO}" "${NEWS_RAG_DIR}"
  if id "${SERVICE_USER}" &>/dev/null; then
    ${SUDO} chown -R "${SERVICE_USER}:${SERVICE_USER}" "${NEWS_RAG_DIR}"
  fi
elif [[ -f "${NEWS_RAG_DIR}/news_rag/app.py" ]]; then
  echo "==> Using repo at ${NEWS_RAG_DIR}"
  cd "${NEWS_RAG_DIR}"
  git fetch origin "${NEWS_RAG_BRANCH}" --depth 1 2>/dev/null || git fetch origin
  git checkout "${NEWS_RAG_BRANCH}"
  git pull origin "${NEWS_RAG_BRANCH}" || true
elif [[ -f "${SCRIPT_DIR}/../../news_rag/app.py" ]]; then
  NEWS_RAG_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
  echo "==> Using existing repo at ${NEWS_RAG_DIR}"
else
  echo "!! Cannot find repo. Set NEWS_RAG_DIR or clone to /opt/news-rag (see deploy/lightsail/DEPLOY.md)"
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
.venv/bin/python scripts/download_embedding_model.py

mkdir -p data/rag_query_logs data/embedding_models data/fund_holdings_aggregate data/nav_cache
if id "${SERVICE_USER}" &>/dev/null; then
  ${SUDO} chown -R "${SERVICE_USER}:${SERVICE_USER}" "${NEWS_RAG_DIR}"
fi

if [[ -f scripts/verify_rag_deploy_data.py ]]; then
  if ! .venv/bin/python scripts/verify_rag_deploy_data.py; then
    echo "!! Fund/metals data missing — run: git pull origin ${NEWS_RAG_BRANCH}"
    exit 1
  fi
fi

if [[ ! -f .env ]]; then
  cp deploy/lightsail/.env.production.example .env
  echo ""
  echo "!! Created ${NEWS_RAG_DIR}/.env — edit QDRANT_* and GEMINI_* keys, then rerun:"
  echo "   nano ${NEWS_RAG_DIR}/.env"
  echo "   sudo NEWS_RAG_DIR=${NEWS_RAG_DIR} bash deploy/lightsail/install.sh"
  exit 0
fi

if grep -q 'YOUR_CLUSTER.cloud.qdrant.io' .env 2>/dev/null; then
  echo "!! Edit .env (QDRANT_URL, QDRANT_API_KEY, GEMINI_API_KEY), then rerun install.sh"
  exit 1
fi

if id "${SERVICE_USER}" &>/dev/null; then
  ${SUDO} chown -R "${SERVICE_USER}:${SERVICE_USER}" "${NEWS_RAG_DIR}"
fi

UNIT=/etc/systemd/system/news-rag.service
sed -e "s|/opt/news-rag|${NEWS_RAG_DIR}|g" \
    -e "s|User=ubuntu|User=${SERVICE_USER}|g" \
    -e "s|Group=ubuntu|Group=${SERVICE_USER}|g" \
    -e "s|--port 8081|--port ${RAG_PORT}|g" \
    deploy/lightsail/news-rag.service > /tmp/news-rag.service
${SUDO} cp /tmp/news-rag.service "${UNIT}"

${SUDO} systemctl daemon-reload
${SUDO} systemctl enable news-rag
${SUDO} systemctl restart news-rag

echo "==> Waiting for /health (imports can take 30–90s on small instances)..."
HEALTH_OK=0
for _ in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:${RAG_PORT}/health" >/dev/null; then
    HEALTH_OK=1
    break
  fi
  sleep 3
done
if [[ "${HEALTH_OK}" -eq 1 ]]; then
  echo "==> OK: http://127.0.0.1:${RAG_PORT}/health"
else
  echo "==> Health check failed after ~120s. Status + logs:"
  ${SUDO} systemctl status news-rag --no-pager -l || true
  ${SUDO} journalctl -u news-rag -n 80 --no-pager
  echo ""
  echo "Try manually: curl -v http://127.0.0.1:${RAG_PORT}/health"
  exit 1
fi

if [[ -f deploy/lightsail/nginx-rag-only.conf ]]; then
  ${SUDO} cp deploy/lightsail/nginx-rag-only.conf /etc/nginx/sites-available/news-rag
  ${SUDO} ln -sf /etc/nginx/sites-available/news-rag /etc/nginx/sites-enabled/news-rag
  ${SUDO} rm -f /etc/nginx/sites-enabled/default
  ${SUDO} nginx -t && ${SUDO} systemctl reload nginx
  echo "==> Nginx: public site http://YOUR_PUBLIC_IP/ -> port ${RAG_PORT}"
fi

if id "${SERVICE_USER}" &>/dev/null; then
  ${SUDO} chown -R "${SERVICE_USER}:${SERVICE_USER}" "${NEWS_RAG_DIR}" || true
fi

echo "==> Done. Open Lightsail firewall: HTTP 80, SSH 22. Do not open ${RAG_PORT} publicly."
