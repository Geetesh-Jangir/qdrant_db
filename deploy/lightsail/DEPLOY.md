# Option A: News RAG only on a new Lightsail instance

Single app: **Qdrant Cloud** + **uvicorn** `news_rag.app:app`. No Rupeestop merge.

## 1. Push this repo to your GitHub

From your PC (example remote — use your repo URL and branch):

```bash
cd "d:\rupeestop work\db_design_with_qdrant_locally"
git remote -v
git push origin huge-corpus
```

Commit includes `data/fund_holdings_aggregate/` (needed for fund ranking). Do **not** commit `.env`.

## 2. Create Lightsail instance

- Ubuntu 22.04+ (2 GB RAM minimum; 4 GB easier for `pip` + embeddings)
- Open ports: **22**, **80** (and **443** later if you add TLS)
- Note the **public IPv4**

## 3. SSH and clone (private repo = use PAT when Git asks for password)

```bash
sudo apt-get update
sudo apt-get install -y git python3-venv python3-pip nginx curl build-essential

export NEWS_RAG_REPO=https://github.com/YOUR_USER/YOUR_REPO.git
export NEWS_RAG_BRANCH=huge-corpus
export NEWS_RAG_DIR=/opt/news-rag

sudo mkdir -p /opt
sudo git clone -b "$NEWS_RAG_BRANCH" "$NEWS_RAG_REPO" "$NEWS_RAG_DIR"
sudo chown -R ubuntu:ubuntu "$NEWS_RAG_DIR"
```

## 4. Configure secrets

```bash
cd /opt/news-rag
cp deploy/lightsail/.env.production.example .env
nano .env
```

Required:

```env
QDRANT_URL=https://xxxx.cloud.qdrant.io
QDRANT_API_KEY=...
RAG_LLM_PROVIDER=gemini
GEMINI_API_KEY=...
```

Optional: `APP_TOKEN=` (if set, API needs `X-App-Token` header)

## 5. Install app + systemd + nginx

```bash
cd /opt/news-rag
sudo NEWS_RAG_DIR=/opt/news-rag bash deploy/lightsail/install.sh
sudo cp deploy/lightsail/nginx-rag-only.conf /etc/nginx/sites-available/news-rag
sudo ln -sf /etc/nginx/sites-available/news-rag /etc/nginx/sites-enabled/news-rag
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

## 6. Verify

```bash
curl -s http://127.0.0.1:8081/health
curl -s http://127.0.0.1/health
```

Browser: `http://YOUR_PUBLIC_IP/` (UI at `/`, API at `/api/ask`)

## Updates after you push code

```bash
cd /opt/news-rag
git pull origin huge-corpus
source .venv/bin/activate
pip install -r requirements.txt -r news_rag/requirements.txt
export PYTHONPATH=/opt/news-rag
python scripts/download_embedding_model.py
sudo systemctl restart news-rag
```

## Troubleshooting

```bash
sudo journalctl -u news-rag -f
```

| Issue | Fix |
|-------|-----|
| `curl raw.githubusercontent.com` 404 | Repo is private — use `git clone`, not raw URLs |
| Health OK on 8081 but not on 80 | Run nginx steps in §5 |
| Empty answers | Fill Qdrant via `python -m news_pipeline` or GitHub Actions pipeline |
