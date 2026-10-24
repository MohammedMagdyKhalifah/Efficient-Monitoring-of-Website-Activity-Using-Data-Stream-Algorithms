#!/bin/bash
set -euo pipefail

cd -- "$(dirname -- "$0")"
repository='https://github.com/MohammedMagdyKhalifah/Efficient-Monitoring-of-Website-Activity-Using-Data-Stream-Algorithms.git'

if [[ ! -d .git ]]; then
  git init -b main
fi

if git remote get-url origin >/dev/null 2>&1; then
  if [[ "$(git remote get-url origin)" != "$repository" ]]; then
    echo 'The existing origin points to a different repository. No remote was changed.' >&2
    exit 1
  fi
else
  git remote add origin "$repository"
fi

# Check GitHub access before changing the index or moving nested metadata.
git ls-remote origin >/dev/null

# Preserve the empty nested repository so the actual web files can be tracked
# together with the Python code, data and report in the main repository.
if [[ -d web/.git ]]; then
  if git -C web rev-parse --verify HEAD >/dev/null 2>&1; then
    echo 'web/ has independent Git history; stopping to preserve it.' >&2
    exit 1
  fi
  mkdir -p tmp/git-metadata-backup
  backup="tmp/git-metadata-backup/web-$(date +%Y%m%d-%H%M%S)-$$.git"
  mv web/.git "$backup"
  echo "Preserved empty nested Git metadata at $backup"
fi

git add -- .
if ! git diff --cached --quiet; then
  git commit -m 'Add complete NASA website activity stream mining project'
fi

git branch -M main
git push -u origin main

# Verify that GitHub received the same commit.
local_commit="$(git rev-parse HEAD)"
remote_commit="$(git ls-remote origin refs/heads/main | cut -f1)"
if [[ "$local_commit" != "$remote_commit" ]]; then
  echo 'Push verification failed: local and remote commits differ.' >&2
  exit 1
fi
echo "Verified GitHub main at $remote_commit"
echo "${repository%.git}"
