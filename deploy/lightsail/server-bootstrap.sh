#!/usr/bin/env bash
# Paste into Lightsail browser SSH (Option A). Set REPO if not using default.
set -euo pipefail

NEWS_RAG_REPO="${NEWS_RAG_REPO:-https://github.com/Geetesh-Jangir/qdrant_db.git}"
NEWS_RAG_BRANCH="${NEWS_RAG_BRANCH:-huge-corpus}"
NEWS_RAG_DIR="${NEWS_RAG_DIR:-/opt/news-rag}"

sudo apt-get update -qq
sudo apt-get install -y git python3-venv python3-pip nginx curl build-essential

if [[ ! -d "${NEWS_RAG_DIR}/.git" ]]; then
  sudo mkdir -p "$(dirname "$NEWS_RAG_DIR")"
  sudo git clone -b "$NEWS_RAG_BRANCH" "$NEWS_RAG_REPO" "$NEWS_RAG_DIR"
  sudo chown -R ubuntu:ubuntu "$NEWS_RAG_DIR"
fi

cd "$NEWS_RAG_DIR"
git fetch origin
git checkout "$NEWS_RAG_BRANCH"
git pull origin "$NEWS_RAG_BRANCH" || true

if [[ ! -f .env ]]; then
  cp deploy/lightsail/.env.production.example .env
  echo "STOP: nano .env then run: sudo NEWS_RAG_DIR=$NEWS_RAG_DIR bash deploy/lightsail/install.sh"
  exit 0
fi

sudo NEWS_RAG_DIR="$NEWS_RAG_DIR" bash deploy/lightsail/install.sh
