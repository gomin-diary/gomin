"""Real concurrent PostgreSQL transactions in a disposable local Docker database.

Usage: python supabase/tests/google-oauth-postgres.py [Supabase DB container]
No environment files or credentials are read. The database is removed in finally.
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

container = sys.argv[1] if len(sys.argv) > 1 else "supabase_db_gomin"
database = "oauth_test_" + uuid4().hex


def sql(statement, db=database):
    result = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", "postgres", "-d", db,
         "-v", "ON_ERROR_STOP=1", "-Atq"],
        input=statement, text=True, capture_output=True, check=True, timeout=20,
    )
    return result.stdout.strip().splitlines()


def digest(value):
    return "decode('" + f"{value:02x}" * 32 + "','hex')"


def call(name, *args):
    return f"select public.gomin_auth_oauth_{name}({','.join(args)});"


def race(*statements):
    barrier = Barrier(len(statements))
    def run(statement):
        barrier.wait(timeout=5)
        lines = sql("begin; set local role service_role; " + statement + "select pg_sleep(0.2); commit;")
        return json.loads(next(line for line in lines if line.startswith("{")))
    with ThreadPoolExecutor(max_workers=len(statements)) as pool:
        return list(pool.map(run, statements))


def signup(proof, binding, session):
    return call("signup", digest(proof), digest(binding), "'이름'", digest(session), "'t'", "'p'", "'t'", "'p'")


def pending(proof, binding, subject, email):
    sql(call("pending_begin", digest(proof), digest(binding), repr(subject), repr(email), "null"))


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    print("PASS", label)


try:
    sql(f"create database {database};", db="postgres")
    for name in ("20261002000000_login_sessions.sql", "20261002010000_signup_verification.sql", "20261004102555_google_oauth.sql", "20261004110048_google_oauth_completion.sql"):
        sql((Path(__file__).resolve().parents[1] / "migrations" / name).read_text())
    sql(call("begin", digest(1), digest(2), "'nonce'", "'cipher'"))
    results = race(call("consume", digest(1), digest(2)), call("consume", digest(1), digest(2)))
    check(sum("nonce" in r for r in results) == 1 and sum(r.get("error") == "OAUTH_REQUEST_INVALID" for r in results) == 1,
          "same authorization request consumed once")

    sql(call("begin", digest(40), digest(41), "'callback'", "'cipher'"))
    sql(call("consume", digest(40), digest(41)))
    results = race(call("complete", digest(40), digest(41), "'completion'", "'completion@example.test'", "'이름'", digest(42), digest(43)),
                   call("complete", digest(40), digest(41), "'completion'", "'completion@example.test'", "'이름'", digest(44), digest(45)))
    check(sum(r.get("new_member") is True for r in results) == 1 and sum(r.get("error") == "OAUTH_REQUEST_INVALID" for r in results) == 1,
          "same consumed callback completes once")
    sql(call("begin", digest(46), digest(47), "'stale'", "'cipher'"))
    sql(call("consume", digest(46), digest(47)))
    sql(call("begin", digest(48), digest(47), "'newer'", "'cipher'"))
    result=json.loads(sql(call("complete", digest(46), digest(47), "'stale'", "'stale@example.test'", "'이름'", digest(49), digest(50)))[0])
    check(result.get("error") == "OAUTH_REQUEST_INVALID", "new browser start blocks an in-flight older callback")

    pending(3, 4, "same-proof", "proof@example.test")
    results = race(signup(3, 4, 5), signup(3, 4, 6))
    check(sum("id" in r for r in results) == 1 and sum(r.get("error") == "OAUTH_PROOF_INVALID" for r in results) == 1,
          "same signup proof creates one member and session")

    pending(7, 8, "email-one", "email@example.test")
    pending(9, 10, "email-two", "email@example.test")
    results = race(signup(7, 8, 11), signup(9, 10, 12))
    check(sum("id" in r for r in results) == 1 and sum(r.get("error") == "EMAIL_EXISTS" for r in results) == 1,
          "different Google subjects racing for one email")

    pending(13, 14, "shared-sub", "sub-one@example.test")
    pending(15, 16, "shared-sub", "sub-two@example.test")
    results = race(signup(13, 14, 17), signup(15, 16, 18))
    check(sum("id" in r for r in results) == 1 and sum(r.get("error") == "OAUTH_LINK_CONFLICT" for r in results) == 1,
          "one Google subject racing with two verified emails")

    sql("insert into public.members(email,name,password_hash) values('existing@example.test','기존','hash');")
    results = race(call("login", "'link-one'", "'existing@example.test'", digest(19)),
                   call("login", "'link-two'", "'existing@example.test'", digest(20)))
    check(sum("id" in r for r in results) == 1 and sum(r.get("error") == "OAUTH_LINK_CONFLICT" for r in results) == 1,
          "automatic linking keeps one identity per member")
    check(sql("select count(*) from public.members;") == ["4"] and sql("select count(*) from public.auth_sessions;") == ["4"]
          and sql("select count(*) from public.member_consents;") == ["6"], "race losers leave no partial members, consents or sessions")

    pending(21, 22, "rollback", "rollback@example.test")
    sql("create function public.reject_consent() returns trigger language plpgsql as $$begin raise exception 'test failure'; end;$$;"
        "create trigger reject_consent before insert on public.member_consents for each row execute function public.reject_consent();")
    try:
        sql("set role service_role; " + signup(21, 22, 23))
        raise AssertionError("trigger must fail")
    except subprocess.CalledProcessError:
        pass
    check(sql("select count(*) from public.members where email='rollback@example.test';") == ["0"]
          and sql("select count(*) from public.member_oauth_identities where subject='rollback';") == ["0"]
          and sql("select count(*) from public.auth_sessions;") == ["4"]
          and sql("select consumed_at is null from public.oauth_pending_actions where subject='rollback';") == ["t"],
          "database failure rolls back member, identity, consent, session and proof consumption")
finally:
    sql(f"drop database if exists {database};", db="postgres")
