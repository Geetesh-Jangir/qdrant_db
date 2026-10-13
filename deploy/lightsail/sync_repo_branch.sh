#!/usr/bin/env bash
# Force local repo to match origin/<branch> (no merge — safe for deploy servers).
# Preserves untracked files such as .env
set -euo pipefail

BRANCH="${1:?usage: sync_repo_branch.sh <branch>}"

# Shallow clones often leave only FETCH_HEAD unless we fetch the ref explicitly.
git fetch origin \
  "+refs/heads/${BRANCH}:refs/remotes/origin/${BRANCH}" \
  --depth 1 2>/dev/null \
  || git fetch origin "${BRANCH}" --depth 1 2>/dev/null \
  || git fetch origin "${BRANCH}"

TARGET=""
if git show-ref --verify --quiet "refs/remotes/origin/${BRANCH}"; then
  TARGET="origin/${BRANCH}"
elif git rev-parse --verify FETCH_HEAD >/dev/null 2>&1; then
  echo "==> Using FETCH_HEAD (no origin/${BRANCH} ref after fetch)"
  TARGET="FETCH_HEAD"
else
  echo "!! Cannot resolve origin/${BRANCH}. Remote branches:"
  git branch -r || true
  exit 1
fi

git checkout -B "${BRANCH}" "${TARGET}"
git reset --hard "${TARGET}"
