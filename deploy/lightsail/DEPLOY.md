# Deploy News RAG on Lightsail (`ask-question`)

Standalone **News RAG** (Option A): Qdrant Cloud + Gemini + this repo. No Rupeestop merge.

**GitHub:** `https://github.com/Geetesh-Jangir/qdrant_db` — branch **`v2`** (or `ask-a-question` / `huge-corpus` for older deploys)

---

## 1. Create instance (AWS Lightsail)

| Setting | Value |
|---------|--------|
| Name | **ask-question** (or any name) |
| OS | Ubuntu 22.04 or 24.04 |
| Plan | **2 GB RAM** or more (512 MB–1 GB works with swap but is slow) |
| Firewall | **SSH 22**, **HTTP 80** |

Note the **public IPv4**. Browser URL: `http://PUBLIC_IP/`

---

## 2. Bootstrap on the server (browser SSH)

**Step A — clone + swap** (works for public or private repo; use a [GitHub PAT](https://github.com/settings/tokens) as the password when `git` asks):

```bash
sudo apt-get update && sudo apt-get install -y git curl
sudo git clone --depth 1 -b v2 https://github.com/Geetesh-Jangir/qdrant_db.git /opt/news-rag
sudo chown -R ubuntu:ubuntu /opt/news-rag
cd /opt/news-rag
bash deploy/lightsail/server-bootstrap.sh
```

If `/opt/news-rag` already exists, skip `git clone` and only run `bash deploy/lightsail/server-bootstrap.sh` from that directory.

**Step B — secrets**

```bash
nano /opt/news-rag/.env
```

Required (no `YOUR_CLUSTER` placeholder):

```env
QDRANT_URL=https://xxxx.cloud.qdrant.io
QDRANT_API_KEY=...
QDRANT_COLLECTION=news_articles
RAG_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-haiku-5-5
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash-lite
PYTHONPATH=/opt/news-rag
```

Primary LLM is **Anthropic**; **Gemini** is used as fallback when the primary call fails. Keep both keys set on the server.

Save: **Ctrl+O**, **Enter**, **Ctrl+X**.

**Step C — install app, systemd, nginx**

```bash
cd /opt/news-rag
sudo NEWS_RAG_DIR=/opt/news-rag bash deploy/lightsail/install.sh
```

---

## 3. Verify

```bash
python3 /opt/news-rag/scripts/verify_rag_deploy_data.py
curl -s http://127.0.0.1:8081/health
curl -s http://127.0.0.1/health
```

Expect `"ok":true`, `"sector_ranking_index":true`, and `"holdings_archive":true`.

Open **`http://PUBLIC_IP/`** → ask a question → **Get Insight** (first ask may take 1–3 minutes).

---

## 4. Updates (after you push from your PC)

Use branch **`v2`** (not `ask-a-question` — that was an old branch name). If `git pull` says *divergent branches*, sync without merging:

```bash
cd /opt/news-rag
unset NEWS_RAG_BRANCH   # if you exported the wrong branch earlier
bash deploy/lightsail/sync_repo_branch.sh v2
source .venv/bin/activate
pip install -r requirements.txt -r news_rag/requirements.txt
deactivate
sudo systemctl restart news-rag
```

---

## Data in git (no SCP)

Committed files power fund screens, sector weights, stock aliases (e.g. BHEL), and metals context. Full list: **`data/DEPLOY_DATA.md`**.

**Not in git:** `.env`, `data/embedding_models/` (downloaded by `install.sh`), `data/nav_cache/` (runtime), Qdrant news corpus.

**Runtime APIs (outbound HTTPS from the instance):** Qdrant Cloud, Anthropic/Gemini/DeepSeek, and RupeeStop NAV/holdings for live fund detail when you ask about specific stocks.

---

## Troubleshooting

```bash
sudo systemctl status news-rag --no-pager -l
sudo journalctl -u news-rag -n 80 --no-pager
curl -v http://127.0.0.1:8081/health
```

If install said health failed but the service is **activating**, wait 60s and run `curl` again — first boot imports many Python modules.

```bash
cd /opt/news-rag && source .venv/bin/activate
export PYTHONPATH=/opt/news-rag
python3 -c "import news_rag.app"   # shows import errors immediately
```

| Issue | Fix |
|-------|-----|
| Site timeout in browser | Lightsail **HTTP 80** open; use `http://` not `https://` |
| `python` not found | Use `python3` or `.venv/bin/python` |
| `Permission denied` on `.venv` or `rag_query_logs` | `sudo chown -R ubuntu:ubuntu /opt/news-rag && sudo systemctl restart news-rag` |
| `git pull` divergent / wrong branch | `unset NEWS_RAG_BRANCH`; `bash deploy/lightsail/sync_repo_branch.sh v2` |
| `pathspec 'ask-a-question'` | Wrong branch env — use `export NEWS_RAG_BRANCH=v2` or `unset NEWS_RAG_BRANCH` |
| `origin/v2` is not a commit | Shallow/broken clone — **reclone** (below) or `git fetch origin +refs/heads/v2:refs/remotes/origin/v2 --depth 1` |
| `sector_to_isin_weights` missing | `bash deploy/lightsail/sync_repo_branch.sh v2` |
| Empty / no news answers | Ingest into Qdrant Cloud (`python -m news_pipeline` or CI) |

**Reclone when git is stuck** (keeps `.env`):

```bash
sudo systemctl stop news-rag 2>/dev/null || true
cp -a /opt/news-rag/.env /tmp/news-rag.env.backup
sudo rm -rf /opt/news-rag
sudo git clone --depth 1 -b v2 https://github.com/Geetesh-Jangir/qdrant_db.git /opt/news-rag
sudo chown -R ubuntu:ubuntu /opt/news-rag
cp -a /tmp/news-rag.env.backup /opt/news-rag/.env
cd /opt/news-rag
sudo NEWS_RAG_DIR=/opt/news-rag NEWS_RAG_BRANCH=v2 bash deploy/lightsail/install.sh
```
