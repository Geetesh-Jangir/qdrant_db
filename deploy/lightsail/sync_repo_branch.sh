#!/usr/bin/env bash
# Force local repo to match origin/<branch> (no merge — safe for deploy servers).
# Preserves untracked files such as .env
set -euo pipefail

BRANCH="${1:?usage: sync_repo_branch.sh <branch>}"
git fetch origin "${BRANCH}" --depth 1 2>/dev/null || git fetch origin "${BRANCH}"
if ! git show-ref --verify --quiet "refs/remotes/origin/${BRANCH}"; then
  echo "!! origin/${BRANCH} not found. Available remote branches:"
  git branch -r
  exit 1
fi
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git checkout "${BRANCH}"
else
  git checkout -B "${BRANCH}" "origin/${BRANCH}"
fi
git reset --hard "origin/${BRANCH}"
