"""Local Supabase setup and development-process supervision; called by dev.sh."""

import argparse
import fcntl
import io
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse

try:
    from dotenv import dotenv_values
except ImportError:
    sys.exit("의존성 설치가 필요합니다. bash scripts/dev.sh를 먼저 실행하세요.")

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "node_modules/.bin/supabase"


def prepare_local_environment() -> dict[str, str]:
    print("로컬 Supabase를 시작합니다. 첫 실행은 이미지 다운로드가 필요합니다.", flush=True)
    # The default status display contains secrets; don't echo it to the terminal.
    subprocess.run([str(CLI), "start"], cwd=ROOT, stdout=subprocess.DEVNULL, check=True)
    subprocess.run([str(CLI), "migration", "up", "--local"], cwd=ROOT, check=True)
    status = subprocess.run(
        [str(CLI), "status", "-o", "env"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    )
    values = dotenv_values(stream=io.StringIO(status.stdout), interpolate=False)
    api_url = values.get("API_URL") or values.get("SUPABASE_URL") or values.get("api.url")
    secret = (
        values.get("SECRET_KEY") or values.get("SUPABASE_SECRET_KEY")
        or values.get("auth.secret_key") or values.get("SERVICE_ROLE_KEY")
        or values.get("SUPABASE_SERVICE_ROLE_KEY") or values.get("auth.service_role_key")
    )
    if not api_url or not secret:
        raise RuntimeError("로컬 Supabase URL/서버 키를 읽지 못했습니다. CLI 버전과 상태를 확인하세요.")
    if urlparse(api_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("개발 스크립트는 로컬 Supabase URL만 허용합니다.")

    environment = os.environ.copy()
    environment.update(
        SUPABASE_URL=api_url,
        SUPABASE_SECRET_KEY=secret,
        CORS_ORIGINS='["http://127.0.0.1:3000","http://localhost:3000"]',
    )
    return environment


def stop_servers(processes: list[subprocess.Popen]) -> None:
    # Each server owns its process group, including Next.js/Uvicorn reload workers.
    for process in processes:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 5
    for process in processes:
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    for process in processes:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def check_port(port: int) -> None:
    deadline = time.monotonic() + 5
    while True:
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind(("127.0.0.1", port))
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"{port} 포트가 다른 프로세스에서 사용 중입니다. 수동 실행한 서버는 직접 종료하세요."
                    ) from None
        time.sleep(0.1)


def restart_servers(
    target: str, processes: dict[str, subprocess.Popen], node_path: str | None = None,
) -> None:
    names = ("frontend", "backend") if target == "all" else (target,)
    commands = {}
    environments = {}
    # Resolve prerequisites before stopping a healthy server.
    if "frontend" in names:
        node = node_path or shutil.which("node")
        next_cli = ROOT / "frontend/node_modules/next/dist/bin/next"
        if not node or not Path(node).is_file() or not os.access(node, os.X_OK) or not next_cli.is_file():
            raise RuntimeError("프론트엔드 설치가 필요합니다. bash scripts/dev.sh를 실행하세요.")
        commands["frontend"] = [node, str(next_cli), "dev", "--hostname", "127.0.0.1", "--port", "3000"]
        environments["frontend"] = dict(os.environ, NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000")
        environments["frontend"]["PATH"] = f"{Path(node).parent}{os.pathsep}{os.environ.get('PATH', '')}"
    if "backend" in names:
        environments["backend"] = prepare_local_environment()
        commands["backend"] = [sys.executable, "-m", "uvicorn", "app.main:app", "--reload",
                               "--host", "127.0.0.1", "--port", "8000"]

    stop_servers([processes.pop(name) for name in names if name in processes])
    for name in names:
        check_port(3000 if name == "frontend" else 8000)
    # Roll back only this request's newly launched processes if spawning fails.
    started = []
    try:
        for name in names:
            processes[name] = subprocess.Popen(
                commands[name], cwd=ROOT / name, env=environments[name], start_new_session=True,
            )
            started.append(name)
    except BaseException:
        stop_servers([processes.pop(name) for name in started])
        raise
    print(f"{target}: 실행 요청 처리. 준비 완료 여부는 서버 로그에서 확인하세요.", flush=True)


def request_restart(target: str) -> int:
    # The owner may still be starting Supabase or applying migrations.
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(600)
        deadline = time.monotonic() + 10
        while True:
            try:
                client.connect(".dev/control.sock")
                break
            except (FileNotFoundError, ConnectionRefusedError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("개발 관리자에 연결하지 못했습니다. 기존 개발 터미널을 확인하세요.") from None
                time.sleep(0.1)
        payload = {"target": target, "node": shutil.which("node")}
        client.sendall((json.dumps(payload) + "\n").encode())
        with client.makefile("r") as reply:
            response = json.loads(reply.readline(8192))
    print(response["message"], flush=True)
    return 0 if response["ok"] else 1


def supervise(target: str) -> int:
    processes: dict[str, subprocess.Popen] = {}
    endpoint = Path(".dev/control.sock")
    # Only the process holding manager.lock can replace a stale endpoint.
    endpoint.unlink(missing_ok=True)
    try:
        with socket.socket(socket.AF_UNIX) as server:
            server.bind(str(endpoint))
            endpoint.chmod(0o600)
            server.listen(8)
            server.settimeout(0.5)
            restart_servers(target, processes)
            print("\n개발 관리자 실행 중. 다른 터미널에서 restart.sh로 대상을 재실행할 수 있습니다.\n"
                  "웹: http://127.0.0.1:3000 · API 문서: http://127.0.0.1:8000/docs\n"
                  "이 터미널의 Ctrl+C: 관리 중인 모든 앱 서버 종료\n", flush=True)
            while True:
                for name, process in list(processes.items()):
                    if process.poll() is not None:
                        stop_servers([processes.pop(name)])
                        print(f"{name} 종료. 다른 서버는 유지합니다. restart.sh로 다시 실행하세요.", flush=True)
                try:
                    connection, _ = server.accept()
                except socket.timeout:
                    continue
                with connection:
                    connection.settimeout(5)
                    try:
                        with connection.makefile("r") as command:
                            payload = json.loads(command.readline(8192))
                        if not isinstance(payload, dict):
                            raise RuntimeError("잘못된 실행 요청입니다.")
                        requested = payload.get("target")
                        node_path = payload.get("node")
                        if node_path is not None and not isinstance(node_path, str):
                            raise RuntimeError("잘못된 Node.js 경로입니다.")
                        if not isinstance(requested, str):
                            raise RuntimeError("실행 대상을 지정하세요.")
                        if requested not in {"frontend", "backend", "all"}:
                            raise RuntimeError("frontend, backend, all 중 하나를 지정하세요.")
                        restart_servers(requested, processes, node_path)
                        response = {"ok": True, "message": f"{requested}: 실행 요청 처리 완료. 로그는 기존 개발 터미널에서 확인하세요."}
                    except subprocess.CalledProcessError:
                        response = {"ok": False, "message": "Supabase 명령 실패. 기존 개발 터미널의 로그를 확인하세요."}
                    except (RuntimeError, OSError, ValueError) as error:
                        response = {"ok": False, "message": str(error)}
                    try:
                        connection.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode())
                    except OSError:
                        pass  # The requesting terminal may have been closed.
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        stop_servers(list(processes.values()))
        endpoint.unlink(missing_ok=True)
        print("관리 중인 앱 서버를 종료했습니다. Supabase 중지: npm run supabase:stop", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="프로젝트 개발 서버 실행/재실행")
    parser.add_argument("target", choices=("frontend", "backend", "all"), nargs="?", default="all")
    args = parser.parse_args()
    os.chdir(ROOT)
    os.umask(0o077)
    Path(".dev").mkdir(mode=0o700, exist_ok=True)
    try:
        with Path(".dev/manager.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return request_restart(args.target)
            return supervise(args.target)
    except KeyboardInterrupt:
        return 130
    except subprocess.CalledProcessError:
        print("Supabase 명령이 실패했습니다. Docker와 로컬 Supabase 상태를 확인하세요.", file=sys.stderr)
        return 1
    except (RuntimeError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    def interrupt(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    sys.exit(main())
