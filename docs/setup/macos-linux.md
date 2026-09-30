# macOS / Linux 설치

공통 진입 파일은 Bash 환경설정 스크립트를 호출합니다. macOS 기본 터미널인 zsh에서도 같은 명령으로 시작할 수 있습니다.

```sh
./scripts/setup.cmd
```

## 준비 사항

- Bash와 `curl` 또는 `wget`: nvm 설치 파일 다운로드에 사용합니다.
- 백엔드를 실행한다면 Python 3.12 이상과 venv 지원
- 백엔드를 실행한다면 설치·실행된 Docker: macOS는 Docker Desktop 또는 OrbStack, Linux는 Docker Engine 또는 Docker Desktop

macOS에서 Homebrew를 사용한다면 Python은 다음과 같이 설치할 수 있습니다.

```sh
brew install python
```

Linux는 배포판에서 제공하는 Python 3.12 이상과 해당 venv 패키지를 설치합니다. Python 3.12 미만으로 생성한 `backend/.venv`가 있다면 따로 옮긴 뒤 설치 명령을 다시 실행하세요. 원하는 Python을 명시하려면 `PYTHON_BIN`에 실행 파일 경로를 지정할 수 있습니다.

```sh
PYTHON_BIN=/path/to/python3 ./scripts/setup.cmd
```

## nvm·Node.js 자동 설치

기존 `NVM_DIR` 또는 표준 경로(`~/.nvm`, `XDG_CONFIG_HOME` 설정 시 그 아래 `nvm`)를 확인하고, Homebrew nvm도 탐색합니다. nvm이 없을 때만 공식 v0.40.8 설치 스크립트를 다운로드해 실행합니다.

새로 설치할 때는 셸 설정 파일에 nvm 로드 구문을 추가합니다. zsh는 `.zshrc`, Bash는 기존 `.bash_profile` 또는 `.bashrc`를 사용합니다. `PROFILE` 환경변수로 직접 지정할 수도 있습니다. Node 버전은 `.nvmrc`를 읽어 설치하고 nvm의 기본 버전으로 설정합니다. 공식 설치 동작은 [nvm 문서](https://github.com/nvm-sh/nvm#installing-and-updating)를 참고하세요.

설치 완료 후 새 터미널을 열고 저장소 루트에서 `npm run dev`를 실행합니다. 셸 설정이 적용되지 않았다면 [문제 해결](../development/troubleshooting.md)을 확인하세요.

## 공통 파일의 실행 권한

`setup.cmd`는 두 종류의 셸이 각자 자기 OS의 스크립트로 연결하도록 작성된 진입 파일입니다. macOS/Linux에서는 확장자와 관계없이 실행 권한이 필요합니다. Git 체크아웃은 저장된 실행 권한을 사용합니다. 압축 파일 등으로 전달받아 권한이 사라졌다면 다음과 같이 복구합니다.

```sh
chmod +x scripts/setup.cmd
./scripts/setup.cmd
```

[공통 설치 안내](README.md)
