#!/usr/bin/env bash
# Compatibility entry point. Installation and server execution are now separate.
set -eo pipefail
SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
printf '설치 명령은 ./scripts/setup.cmd로 통합되었습니다. 설치 후 npm run dev를 실행하세요.\n'
exec bash "$SCRIPT_DIRECTORY/setup.sh" "$@"
