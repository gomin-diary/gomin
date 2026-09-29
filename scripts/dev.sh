#!/usr/bin/env bash
# macOS (including Bash 3.2) and Linux. Run with bash, not source.
set -eo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
DEV_MODE=install
DEV_TARGET=all
if [[ $# -gt 0 ]]; then
  if [[ $# -ne 2 || "$1" != "--restart" ]]; then
    printf '사용법: bash scripts/dev.sh 또는 bash scripts/restart.sh {frontend|backend|all}\n' >&2
    exit 1
  fi
  case "$2" in
    frontend|backend|all) DEV_MODE=restart; DEV_TARGET="$2" ;;
    *) printf '지원하지 않는 실행 대상입니다.\n' >&2; exit 1 ;;
  esac
  if [[ ! -x backend/.venv/bin/python ]]; then
    printf '최초 설치가 필요합니다. bash scripts/dev.sh를 먼저 실행하세요.\n' >&2
    exit 1
  fi
fi

show_nvm_help() {
  cat <<'HELP'
nvm을 찾을 수 없습니다. 아래 방법 중 하나로 설치한 뒤 다시 실행하세요.

[curl — macOS / Linux]
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

XDG_CONFIG_HOME을 사용하면 설치 경로가 "$XDG_CONFIG_HOME/nvm"일 수 있습니다.
설치 프로그램이 안내한 NVM_DIR을 사용하세요.
HELP
  if [[ "$(uname -s)" == "Darwin" ]]; then
    cat <<'HELP'

[Homebrew — macOS]
# Homebrew가 없다면 https://brew.sh 에서 먼저 설치하세요.
brew install nvm
mkdir -p "$HOME/.nvm"
export NVM_DIR="$HOME/.nvm"
. "$(brew --prefix nvm)/nvm.sh"

위 export와 로드 명령을 ~/.zshrc에도 추가하면 새 터미널에 적용됩니다.
HELP
  fi
  printf '\n설치 후 실행: bash scripts/dev.sh\n'
}

# Backend-only restarts don't require Node.js.
if [[ "$DEV_TARGET" != backend ]]; then
# nvm is a shell function; non-interactive shells must load it explicitly.
if ! command -v nvm >/dev/null 2>&1; then
  if [[ -z "${NVM_DIR:-}" ]]; then
    if [[ -n "${XDG_CONFIG_HOME:-}" ]]; then
      export NVM_DIR="$XDG_CONFIG_HOME/nvm"
    else
      export NVM_DIR="$HOME/.nvm"
    fi
  fi
  if [[ -s "$NVM_DIR/nvm.sh" ]]; then
    . "$NVM_DIR/nvm.sh" --no-use
  elif command -v brew >/dev/null 2>&1; then
    NVM_BREW_PREFIX="$(brew --prefix nvm 2>/dev/null || true)"
    if [[ -n "$NVM_BREW_PREFIX" && -s "$NVM_BREW_PREFIX/nvm.sh" ]]; then
      . "$NVM_BREW_PREFIX/nvm.sh" --no-use
    fi
  fi
fi
if ! command -v nvm >/dev/null 2>&1; then
  show_nvm_help
  exit 1
fi
fi

if [[ "$DEV_TARGET" != frontend ]]; then
if ! command -v docker >/dev/null 2>&1; then
  printf 'Docker CLI가 필요합니다. Docker Desktop 또는 OrbStack을 설치하고 CLI 연동을 활성화하세요.\n' >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  printf 'Docker에 연결할 수 없습니다. Docker Desktop 또는 OrbStack을 실행한 뒤 다시 시도하세요.\n' >&2
  exit 1
fi
fi

if [[ -x backend/.venv/bin/python ]]; then
  DEV_PYTHON="$PROJECT_ROOT/backend/.venv/bin/python"
elif [[ -n "${PYTHON_BIN:-}" ]]; then
  DEV_PYTHON="$PYTHON_BIN"
elif command -v python3.12 >/dev/null 2>&1; then
  DEV_PYTHON="$(command -v python3.12)"
elif command -v brew >/dev/null 2>&1; then
  PYTHON_BREW_PREFIX="$(brew --prefix python@3.12 2>/dev/null || true)"
  DEV_PYTHON="$PYTHON_BREW_PREFIX/bin/python3.12"
else
  DEV_PYTHON=""
fi
if [[ -z "$DEV_PYTHON" ]] || ! "$DEV_PYTHON" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))' 2>/dev/null; then
  printf 'Python 3.12가 필요합니다. macOS: brew install python@3.12\n' >&2
  printf 'Linux: Python 3.12와 venv 지원을 설치하세요. PYTHON_BIN으로 실행 파일을 지정할 수 있습니다.\n' >&2
  printf '기존 backend/.venv가 다른 Python 버전이면 해당 가상환경을 별도로 옮긴 후 다시 실행하세요.\n' >&2
  exit 1
fi

if [[ "$DEV_MODE" == install ]]; then
"$DEV_PYTHON" - <<'PY'
import fcntl
from pathlib import Path
import sys

lock_path = Path('.dev/manager.lock')
if lock_path.exists():
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('개발 서버가 관리 중입니다. 재실행은 bash scripts/restart.sh all을 사용하세요.', file=sys.stderr)
            print('의존성을 다시 설치하려면 기존 개발 터미널에서 Ctrl+C로 먼저 종료하세요.', file=sys.stderr)
            sys.exit(1)
PY
printf '\nNode.js와 의존성을 설치합니다.\n'
nvm install
nvm use
npm ci --no-audit --no-fund
npm --prefix frontend ci --no-audit --no-fund
if [[ ! -x backend/.venv/bin/python ]]; then
  "$DEV_PYTHON" -m venv backend/.venv
fi
backend/.venv/bin/python -m pip install -r backend/requirements.txt
elif [[ "$DEV_TARGET" != backend ]]; then
  nvm use || { printf 'Node.js 설치가 필요합니다. bash scripts/dev.sh를 실행하세요.\n' >&2; exit 1; }
fi

# Only create missing files. Local credentials are passed to the child process.
umask 077
[[ -f backend/.env ]] || cp backend/.env.example backend/.env
[[ -f frontend/.env.local ]] || cp frontend/.env.example frontend/.env.local

exec backend/.venv/bin/python scripts/dev.py "$DEV_TARGET"
