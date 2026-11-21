#!/bin/bash
# Deploy exactly the tested source and corpus pins. Pull GHCR when public; build
# from the same inputs when package access is private. No registry credentials needed.
set -euo pipefail
source_sha=$1
corpus_sha=$2
image=$3
[[ $source_sha =~ ^[0-9a-f]{40}$ && $corpus_sha =~ ^[0-9a-f]{40}$ ]]
[[ $image =~ ^ghcr\.io/sobot/global-law:[0-9a-f-]+$ ]]
cd /opt/serbia-law-mcp
test "$(git rev-parse HEAD)" = "$source_sha"
git submodule update --init serbia/national/acts
git -C serbia/national/acts fetch origin "$corpus_sha"
git -C serbia/national/acts checkout --detach "$corpus_sha"
if ! git diff --quiet -- serbia/national/acts; then
  git -c user.name=deployment -c user.email=deployment@localhost commit -am "Pin corpus $corpus_sha"
fi
docker pull "$image" || docker build -t "$image" .
name=serbia-law-mcp
backup=serbia-law-mcp-previous
if docker container inspect "$backup" >/dev/null 2>&1; then docker rm -f "$backup"; fi
if docker container inspect "$name" >/dev/null 2>&1; then
  docker stop "$name"
  docker rename "$name" "$backup"
fi
if docker run -d --restart unless-stopped --name "$name" --memory 1600m --memory-swap 3500m -p 127.0.0.1:8080:8080 "$image" && \
   curl --fail --retry 25 --retry-all-errors --retry-delay 3 http://127.0.0.1:8080/health; then
  if docker container inspect "$backup" >/dev/null 2>&1; then docker rm "$backup"; fi
else
  docker logs --tail 50 "$name" || true
  docker rm -f "$name" || true
  if docker container inspect "$backup" >/dev/null 2>&1; then docker rename "$backup" "$name"; docker start "$name"; fi
  exit 1
fi
