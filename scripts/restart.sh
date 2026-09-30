#!/usr/bin/env bash
# Compatibility entry point. Prefer npm run dev:frontend / dev:backend / dev:all.
set -eo pipefail
if [[ $# -ne 1 ]]; then printf '사용법: bash scripts/restart.sh {frontend|backend|all}\n' >&2; exit 1; fi
case "$1" in frontend|backend|all) ;; *) printf '실행 대상은 frontend, backend, all 중 하나입니다.\n' >&2; exit 1 ;; esac
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
if [[ -z "${NVM_DIR:-}" ]]; then
  if [[ -n "${XDG_CONFIG_HOME:-}" ]]; then export NVM_DIR="$XDG_CONFIG_HOME/nvm";
  else export NVM_DIR="$HOME/.nvm"; fi
fi
if [[ -s "$NVM_DIR/nvm.sh" ]]; then . "$NVM_DIR/nvm.sh" --no-use; nvm use; fi
if ! command -v node >/dev/null 2>&1; then printf 'Node.js를 찾을 수 없습니다. ./scripts/setup.cmd를 실행하고 새 터미널을 여세요.\n' >&2; exit 1; fi
exec node scripts/dev.mjs "$1"
