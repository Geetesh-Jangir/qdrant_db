#!/usr/bin/env bash
# Fresh Lightsail instance "ask-question" — paste into browser SSH (step 1).
# Private GitHub repo: use a PAT when git asks for a password, or:
#   export NEWS_RAG_REPO=https://YOUR_TOKEN@github.com/Geetesh-Jangir/qdrant_db.git
set -euo pipefail

NEWS_RAG_REPO="${NEWS_RAG_REPO:-https://github.com/Geetesh-Jangir/qdrant_db.git}"
NEWS_RAG_BRANCH="${NEWS_RAG_BRANCH:-huge-corpus}"
NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"

echo "==> Bootstrap News RAG (ask-question / Option A)"

if ! swapon --show 2>/dev/null | grep -q swapfile; then
  echo "==> Adding 2G swap (helps pip + git on small instances)"
  sudo fallocate -l 2G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  if ! grep -q '^/swapfile ' /etc/fstab 2>/dev/null; then
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  fi
fi

sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git python3 python3-venv python3-pip nginx curl build-essential python-is-python3

if [[ ! -d "${NEWS_RAG_DIR}/.git" ]]; then
  sudo mkdir -p "$(dirname "$NEWS_RAG_DIR")"
  sudo git clone --depth 1 -b "$NEWS_RAG_BRANCH" "$NEWS_RAG_REPO" "$NEWS_RAG_DIR"
  sudo chown -R ubuntu:ubuntu "$NEWS_RAG_DIR"
fi

cd "$NEWS_RAG_DIR"
git fetch origin "$NEWS_RAG_BRANCH" --depth 1 2>/dev/null || git fetch origin
git checkout "$NEWS_RAG_BRANCH"
git pull origin "$NEWS_RAG_BRANCH" || true

if [[ ! -f .env ]]; then
  cp deploy/lightsail/.env.production.example .env
  echo ""
  echo "=== NEXT: edit secrets ==="
  echo "  nano ${NEWS_RAG_DIR}/.env"
  echo "  (QDRANT_URL, QDRANT_API_KEY, GEMINI_API_KEY — remove YOUR_CLUSTER placeholder)"
  echo ""
  echo "=== THEN install ==="
  echo "  sudo NEWS_RAG_DIR=${NEWS_RAG_DIR} bash deploy/lightsail/install.sh"
  echo ""
  echo "Lightsail console -> instance ask-question -> Networking -> open HTTP (80)"
  exit 0
fi

sudo NEWS_RAG_DIR="$NEWS_RAG_DIR" bash deploy/lightsail/install.sh
