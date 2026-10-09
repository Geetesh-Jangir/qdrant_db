#!/usr/bin/env bash
# Sync data/news_runs and data/news_backfill to Cloudflare R2 (S3 API).
# Requires: aws CLI v2 configured for R2, or set AWS_ENDPOINT_URL.
set -euo pipefail

ROOT="${NEWS_RAG_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
ACCOUNT_ID="${R2_ACCOUNT_ID:?set R2_ACCOUNT_ID}"
BUCKET="${R2_BUCKET:?set R2_BUCKET}"
ENDPOINT="${AWS_ENDPOINT_URL:-https://${ACCOUNT_ID}.r2.cloudflarestorage.com}"

export AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID:?set R2_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY:?set R2_SECRET_ACCESS_KEY}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-auto}"

aws --endpoint-url "${ENDPOINT}" s3 sync "${ROOT}/data/news_runs" "s3://${BUCKET}/news_runs" --only-show-errors
aws --endpoint-url "${ENDPOINT}" s3 sync "${ROOT}/data/news_backfill" "s3://${BUCKET}/news_backfill" --only-show-errors
aws --endpoint-url "${ENDPOINT}" s3 sync "${ROOT}/data/news_failures" "s3://${BUCKET}/news_failures" --only-show-errors
echo "==> synced to s3://${BUCKET}/"
