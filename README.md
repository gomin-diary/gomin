# Gomin

## 설치

[설치 안내](docs/local-development/setup/README.md)의 준비 사항을 확인한 뒤, 저장소 루트에서 실행합니다. **Windows PowerShell, macOS/Linux 터미널 모두 같은 명령을 사용합니다.**

```sh
./scripts/setup.cmd
```

nvm·Node.js와 프로젝트 의존성을 설치합니다. 설치가 끝나면 새 터미널을 열고 저장소 루트로 이동하세요.

## 실행

```sh
npm run dev
```

- 웹: http://127.0.0.1:3000
- API 문서: http://127.0.0.1:8000/docs
- 종료: 실행 중인 터미널에서 `Ctrl+C`

대상별 시작·재시작은 다른 터미널에서 실행합니다.

```sh
npm run dev:frontend
npm run dev:backend
npm run dev:all
```

Supabase까지 중지하려면 `npm run supabase:stop`을 실행합니다.

상세 안내: [실행·재시작·종료](docs/local-development/runtime.md) · [서버 개별 실행](docs/local-development/manual-run.md)
