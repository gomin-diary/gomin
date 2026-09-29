#!/usr/bin/env bash
set -eo pipefail

case "${1:-}" in
  frontend|backend|all)
    if [[ $# -ne 1 ]]; then
      printf '사용법: bash scripts/restart.sh {frontend|backend|all}\n' >&2
      exit 1
    fi
    ;;
  *)
    printf '사용법: bash scripts/restart.sh {frontend|backend|all}\n' >&2
    exit 1
    ;;
esac

SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIRECTORY/dev.sh" --restart "$1"
