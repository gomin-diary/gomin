#!/usr/bin/env bash
# Compatible with macOS Bash 3.2 and Linux Bash.
set -eo pipefail

usage() {
  printf '사용법: ./scripts/setup.cmd [all|frontend|backend]\n'
  printf 'nvm·Node.js와 선택한 대상의 의존성을 설치합니다. 기본값: all\n'
  printf '설치 후 새 터미널에서 npm run dev를 실행하세요.\n'
}
if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then usage; exit 0; fi
SETUP_TARGET="${1:-all}"
if [[ $# -gt 1 ]]; then usage >&2; exit 1; fi
case "$SETUP_TARGET" in all|frontend|backend) ;; *) usage >&2; exit 1 ;; esac
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Check an existing manager before switching Node or replacing dependencies.
if [[ -f .dev/manager.guard ]]; then
  printf '실행기 잠금 작업이 진행 중입니다. docs/development/troubleshooting.md를 확인하세요.\n' >&2
  exit 1
fi
if [[ -f .dev/manager.lock ]]; then
  SETUP_MANAGER_PID="$(cat .dev/manager.lock)"
  case "$SETUP_MANAGER_PID" in
    ''|*[!0-9]*) ;;
    *)
      if [[ "$SETUP_MANAGER_PID" -gt 0 ]] && kill -0 "$SETUP_MANAGER_PID" 2>/dev/null; then
        printf '개발 실행기가 켜져 있습니다. 기존 개발 터미널에서 Ctrl+C로 종료한 뒤 설치하세요.\n' >&2
        exit 1
      fi ;;
  esac
fi
if [[ -z "${NVM_DIR:-}" ]]; then
  if [[ -n "${XDG_CONFIG_HOME:-}" ]]; then export NVM_DIR="$XDG_CONFIG_HOME/nvm";
  else export NVM_DIR="$HOME/.nvm"; fi
fi
if [[ -s "$NVM_DIR/nvm.sh" ]]; then
  . "$NVM_DIR/nvm.sh" --no-use
elif command -v brew >/dev/null 2>&1; then
  NVM_BREW_PREFIX="$(brew --prefix nvm 2>/dev/null || true)"
  if [[ -n "$NVM_BREW_PREFIX" && -s "$NVM_BREW_PREFIX/nvm.sh" ]]; then . "$NVM_BREW_PREFIX/nvm.sh" --no-use; fi
fi
if ! command -v nvm >/dev/null 2>&1; then
  printf '\nnvm을 설치합니다. 셸 설정에 nvm 로드 구문이 추가됩니다.\n'
  NVM_INSTALLER="$(mktemp)"
  trap 'rm -f "$NVM_INSTALLER"' EXIT
  NVM_INSTALL_URL='https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh'
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --retry 3 "$NVM_INSTALL_URL" -o "$NVM_INSTALLER"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$NVM_INSTALL_URL" -O "$NVM_INSTALLER"
  else
    printf 'nvm 다운로드에 curl 또는 wget이 필요합니다. 설치 후 다시 실행하세요.\n' >&2
    exit 1
  fi
  # Give the official installer a real profile even on a fresh user account.
  if [[ -z "${PROFILE:-}" ]]; then
    case "${SHELL:-/bin/bash}" in
      */zsh) export PROFILE="${ZDOTDIR:-$HOME}/.zshrc" ;;
      *)
        if [[ -f "$HOME/.bash_profile" ]]; then export PROFILE="$HOME/.bash_profile";
        else export PROFILE="$HOME/.bashrc"; fi ;;
    esac
  fi
  touch "$PROFILE"
  mkdir -p "$NVM_DIR"
  bash "$NVM_INSTALLER"
  . "$NVM_DIR/nvm.sh" --no-use
fi
NODE_VERSION="$(tr -d '[:space:]' < .nvmrc)"
printf '\nNode.js %s를 준비합니다.\n' "$NODE_VERSION"
nvm install "$NODE_VERSION"
nvm use "$NODE_VERSION"
nvm alias default "$NODE_VERSION"
node scripts/dev.mjs --check-idle

if [[ "$SETUP_TARGET" != frontend ]]; then
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    printf 'Docker가 필요합니다. Docker를 설치·실행한 뒤 다시 시도하세요. 안내: docs/setup/macos-linux.md\n' >&2
    exit 1
  fi
  SETUP_PYTHON=''
  if [[ -x backend/.venv/bin/python ]]; then
    SETUP_PYTHON="$PROJECT_ROOT/backend/.venv/bin/python"
  elif [[ -n "${PYTHON_BIN:-}" ]]; then
    SETUP_PYTHON="$PYTHON_BIN"
  else
    for candidate in python3 python3.12; do
      if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info[:2] < (3, 12))' 2>/dev/null; then
        SETUP_PYTHON="$(command -v "$candidate")"; break
      fi
    done
    if [[ -z "$SETUP_PYTHON" ]] && command -v brew >/dev/null 2>&1; then
      for formula in python python@3.12; do
        PYTHON_BREW_PREFIX="$(brew --prefix "$formula" 2>/dev/null || true)"
        [[ -n "$PYTHON_BREW_PREFIX" ]] || continue
        for candidate in "$PYTHON_BREW_PREFIX/bin/python3" "$PYTHON_BREW_PREFIX/bin/python3.12"; do
          if [[ -x "$candidate" ]] && "$candidate" -c 'import sys; sys.exit(sys.version_info[:2] < (3, 12))' 2>/dev/null; then
            SETUP_PYTHON="$candidate"; break 2
          fi
        done
      done
    fi
  fi
  if [[ -z "$SETUP_PYTHON" ]] || ! "$SETUP_PYTHON" -c 'import sys; sys.exit(sys.version_info[:2] < (3, 12))' 2>/dev/null; then
    printf 'Python 3.12 이상이 필요합니다. 안내: docs/setup/macos-linux.md\n' >&2
    printf 'PYTHON_BIN으로 경로를 지정할 수 있습니다. 기존 backend/.venv의 Python이 3.12 미만이면 해당 폴더를 옮긴 뒤 다시 실행하세요.\n' >&2
    exit 1
  fi
fi

printf '\n프로젝트 의존성을 설치합니다.\n'
npm ci --no-audit --no-fund
umask 077
if [[ "$SETUP_TARGET" != backend ]]; then
  npm --prefix frontend ci --no-audit --no-fund
  [[ -f frontend/.env.local ]] || cp frontend/.env.example frontend/.env.local
fi
if [[ "$SETUP_TARGET" != frontend ]]; then
  if [[ ! -x backend/.venv/bin/python ]]; then "$SETUP_PYTHON" -m venv backend/.venv; fi
  backend/.venv/bin/python -m pip install -r backend/requirements.txt
  [[ -f backend/.env ]] || cp backend/.env.example backend/.env
fi
printf '\n설치 완료. 새 터미널을 열고 저장소 루트에서 실행하세요: npm run dev:%s\n' "$SETUP_TARGET"
printf '설치 단계에서는 앱 서버와 Supabase를 시작하지 않습니다.\n'
