#!/bin/bash
# Deploy the tested source and corpus pins using a reusable runtime image.
set -euo pipefail
source_sha=$1
corpus_sha=$2
image=$3
[[ $source_sha =~ ^[0-9a-f]{40}$ && $corpus_sha =~ ^[0-9a-f]{40}$ ]]
[[ $image =~ ^ghcr\.io/sobot/global-law:runtime-[0-9a-f]{32}$ ]]
cd /opt/serbia-law-mcp
repo=$(pwd)
corpus=serbia/national/acts
cache="$repo/.git/global-law-cache"
name=serbia-law-mcp
backup=serbia-law-mcp-previous

# Never overlap two SSM deployments or overwrite a recovery container.
exec 9>/var/lock/serbia-law-mcp-deploy.lock
flock -n 9
if docker container inspect "$backup" >/dev/null 2>&1; then
  echo "Recovery container exists; inspect it before redeploying." >&2
  exit 1
fi

old_root=$(git rev-parse HEAD)
was_sparse=$(git config --bool core.sparseCheckout || echo false)
old_corpus=
if [[ -e "$corpus/.git" ]]; then
  old_corpus=$(git -C "$corpus" rev-parse HEAD)
  # Download new objects while the old MCP continues to serve its pinned tree.
  if ! git -C "$corpus" cat-file -e "$corpus_sha^{commit}" 2>/dev/null; then
    git -C "$corpus" fetch origin "$corpus_sha"
  fi
fi

# The same source/corpus is already deployed: avoid checkout and restart.
if [[ $(docker inspect --format '{{index .Config.Labels "serbia.source"}}' "$name" 2>/dev/null || true) == "$source_sha" &&
      $(docker inspect --format '{{index .Config.Labels "serbia.corpus"}}' "$name" 2>/dev/null || true) == "$corpus_sha" &&
      $old_corpus == "$corpus_sha" &&
      $(git ls-tree HEAD "$corpus" | awk '{print $3}') == "$corpus_sha" ]] &&
      curl --fail --silent http://127.0.0.1:8080/health >/dev/null; then
  echo "Already running the tested pins."
  exit 0
fi

# Pull/build only the small runtime image, before interrupting the current app.
if ! docker image inspect "$image" >/dev/null 2>&1 && ! docker pull "$image"; then
  context=$(mktemp -d)
  (
    trap 'rm -f "$context/Dockerfile" "$context/requirements-serbia.txt"; rmdir "$context"' EXIT
    git show "$source_sha:Dockerfile" > "$context/Dockerfile"
    git show "$source_sha:requirements-serbia.txt" > "$context/requirements-serbia.txt"
    docker build -t "$image" "$context"
  )
fi
install -d -o 10001 -g 10001 -m 0755 "$cache"

# The running container bind-mounts this checkout. Stop it before moving HEAD;
# any failure restores its original pins before restarting it.
had_old=false
changed=false
new_started=false
rollback() {
  local status=$?
  trap - EXIT
  if (( status == 0 )); then return; fi
  set +e
  if "$new_started"; then
    docker logs --tail 50 "$name" || true
    docker rm -f "$name"
  fi
  if "$changed"; then
    git checkout --no-recurse-submodules --detach "$old_root" &&
      { [[ $was_sparse == true ]] || git sparse-checkout disable; } &&
      { [[ -z "$old_corpus" ]] || git -C "$corpus" checkout --detach "$old_corpus"; } ||
      { echo "Failed to restore the previous Git pins; manual recovery required." >&2; exit "$status"; }
  fi
  if "$had_old"; then
    if docker container inspect "$backup" >/dev/null 2>&1; then
      docker rename "$backup" "$name" && docker start "$name"
    else
      docker start "$name"
    fi
  fi
  exit "$status"
}
trap rollback EXIT
if docker container inspect "$name" >/dev/null 2>&1; then
  had_old=true
  docker stop "$name"
  docker rename "$name" "$backup"
fi
changed=true
# Use the same runtime and test paths as the Serbia CI checkout.
git sparse-checkout set --cone data plugins/sr serbia tests tools
git checkout --no-recurse-submodules --detach "$source_sha"
if [[ ! -e "$corpus/.git" ]]; then
  git submodule update --init -- "$corpus"
fi
if ! git -C "$corpus" cat-file -e "$corpus_sha^{commit}" 2>/dev/null; then
  git -C "$corpus" fetch origin "$corpus_sha"
fi
test "$(git -C "$corpus" rev-parse --is-shallow-repository)" = false
git -C "$corpus" checkout --detach "$corpus_sha"
if ! git diff --quiet -- "$corpus"; then
  git add -- "$corpus"
  git -c user.name=deployment -c user.email=deployment@localhost commit -m "Pin corpus $corpus_sha" -- "$corpus"
fi
test "$(git ls-tree HEAD "$corpus" | awk '{print $3}')" = "$corpus_sha"

new_started=true
docker run -d --restart unless-stopped --name "$name" \
  --memory 1600m --memory-swap 3500m -p 127.0.0.1:8080:8080 \
  --label "serbia.source=$source_sha" --label "serbia.corpus=$corpus_sha" \
  --mount "type=bind,src=$repo,dst=/app,readonly" \
  --mount "type=bind,src=$cache,dst=/app/.git/global-law-cache" \
  "$image"
curl --fail --retry 25 --retry-all-errors --retry-delay 3 http://127.0.0.1:8080/health
trap - EXIT
if "$had_old"; then docker rm "$backup"; fi
