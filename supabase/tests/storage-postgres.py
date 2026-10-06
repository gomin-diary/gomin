"""Verify Storage migration in a disposable database using schema-only Supabase definitions.

Usage: python supabase/tests/storage-postgres.py [Supabase DB container]
No environment files, keys or application data are read. The database is removed in finally.
"""
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

container = sys.argv[1] if len(sys.argv) > 1 else 'supabase_db_gomin'
database = 'storage_test_' + uuid4().hex
root = Path(__file__).resolve().parents[1]


def sql(statement, db=database):
    result = subprocess.run(
        ['docker', 'exec', '-i', container, 'psql', '-U', 'postgres', '-d', db,
         '-v', 'ON_ERROR_STOP=1', '-Atq'],
        input=statement, text=True, capture_output=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip().splitlines()


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    print('PASS', label)


try:
    sql(f'create database {database};', db='postgres')
    # Only schema definitions are copied; no existing bucket/object/auth rows are included.
    schema = subprocess.run(
        ['docker', 'exec', container, 'pg_dump', '-U', 'postgres', '-d', 'postgres',
         '--schema-only', '--no-owner', '--no-privileges', '--schema=auth', '--schema=storage'],
        text=True, capture_output=True, check=True, timeout=30,
    ).stdout
    sql('create schema if not exists extensions; '
        'create extension if not exists "uuid-ossp" with schema extensions; '
        'create extension if not exists pgcrypto with schema extensions; ' + schema)
    sql('grant usage on schema storage to anon, authenticated, service_role; '
        'grant select, insert, update, delete on storage.buckets, storage.objects to anon, authenticated, service_role;')
    sql("insert into storage.buckets(id,name,public,file_size_limit) values('unrelated','unrelated',true,123);")
    for migration in sorted((root / 'migrations').glob('*.sql')):
        sql(migration.read_text())
    check(sql("select name, public, file_size_limit from storage.buckets where id='gomin-files';")
          == ['gomin-files|f|10485760'], 'full migration chain creates private 10MiB bucket')
    check(sql("select name, public, file_size_limit from storage.buckets where id='unrelated';")
          == ['unrelated|t|123'], 'unrelated bucket is preserved')
    migration = next((root / 'migrations').glob('*_file_storage_bucket.sql')).read_text()
    sql(migration)
    check(sql("select count(*) from storage.buckets where id='gomin-files';") == ['1'], 'bucket migration is repeatable')
    check(sql("begin; set local role anon; select count(*) from storage.buckets where id='gomin-files'; rollback;") == ['0'],
          'anonymous role cannot read private bucket metadata')
    check(sql("select count(*) from pg_policies where schemaname='storage' and tablename='objects';") == ['0'],
          'no general browser object policy is introduced')
finally:
    sql(f'drop database if exists {database};', db='postgres')
