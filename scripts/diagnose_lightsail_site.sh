#!/usr/bin/env bash
# Run on the Lightsail instance after deploy. Checks app (8081), nginx (80), and common misconfig.
set -euo pipefail

RAG_PORT="${RAG_PORT:-8081}"
PUBLIC_HINT="${1:-}"

echo "==> news-rag service"
systemctl is-active news-rag 2>/dev/null || echo "inactive"
systemctl status news-rag --no-pager -l 2>/dev/null | tail -n 8 || true

echo ""
echo "==> Backend health (127.0.0.1:${RAG_PORT}/health)"
curl -sf "http://127.0.0.1:${RAG_PORT}/health" | python3 -m json.tool 2>/dev/null || {
  echo "FAILED — app not listening on ${RAG_PORT}"
  journalctl -u news-rag -n 30 --no-pager 2>/dev/null || true
  exit 1
}

echo ""
echo "==> Nginx + UI (127.0.0.1:80)"
# Use GET (curl -I / HEAD often returns 405 on FastAPI HTML routes; Chrome uses GET).
CODE_ROOT=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1/" || echo "000")
CODE_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1/health" || echo "000")
echo "GET / -> HTTP ${CODE_ROOT}"
echo "GET /health -> HTTP ${CODE_HEALTH}"
HEAD_ROOT=$(curl -sI -o /dev/null -w "%{http_code}" "http://127.0.0.1/" || echo "000")
if [[ "${HEAD_ROOT}" == "405" && "${CODE_ROOT}" == "200" ]]; then
  echo "(HEAD / -> HTTP 405 is expected; ignore curl -I — use GET as above)"
fi
if [[ "${CODE_ROOT}" != "200" ]]; then
  echo "!! Home page failed — check: sudo nginx -t && sudo systemctl status nginx"
  exit 1
fi
HEAD=$(curl -sf "http://127.0.0.1/" | head -c 120 || true)
if [[ "${HEAD}" != *"html"* && "${HEAD}" != *"HTML"* ]]; then
  echo "!! / did not return HTML: ${HEAD}"
fi

TOKEN_REQUIRED=$(curl -sf "http://127.0.0.1:${RAG_PORT}/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('app_token_required', False))" 2>/dev/null || echo "?")
echo ""
echo "app_token_required=${TOKEN_REQUIRED}"
if [[ "${TOKEN_REQUIRED}" == "True" ]]; then
  echo "!! APP_TOKEN is set in .env — browser must use ?app_token=... or unset APP_TOKEN for open access."
fi

echo ""
echo "embeddings_ready may be false for ~1–2 min after restart (background warmup). Ask still works; first query loads the model."

if [[ -n "${PUBLIC_HINT}" ]]; then
  echo ""
  echo "From your PC use: http://${PUBLIC_HINT}/  (not https:// unless you configured TLS)"
  echo "Lightsail Networking must allow HTTP port 80."
fi
