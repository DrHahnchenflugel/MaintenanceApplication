#!/usr/bin/env bash
set -euo pipefail

echo "[-] Disk usage:"
df -h / | sed -n '1,2p'

# Resolve repo root even if called by sym link or from another dir
REPO_ROOT="$(cd -- "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$REPO_ROOT"

echo "[-] GIT PULL in $REPO_ROOT"
git pull
echo "[v] GIT PULL SUCCESS"

echo "[-] Docker compose build --pull"
docker compose build --pull
echo "[v] Docker compose build --pull SUCCESS"

echo "[-] Pruning unused images + build cache"
docker image prune -f
docker builder prune -f
echo "[v] Prune done"

echo "[-] Docker compose up -d"
docker compose up -d
echo "[v] Docker compose up -d SUCCESS"

echo "[v] STATUS"
docker compose ps
 
