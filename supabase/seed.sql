-- GOMIN-58: Local development fixtures only. Never apply this seed to production.
-- Test-only shared password and instructions: docs/local-development/test-users.md.
-- Insert consent fixtures only for accounts created by this statement.
with created as (
    insert into public.members(id,email,name,password_hash)
    values
    ('00000000-0000-4000-8000-000000000001'::uuid, 'user1@gomin.today', '로컬 사용자 1', 'scrypt$32768$8$3$373a6cd10b755db556536436229e7353$67675fe460fb4d7f5c5ef64051ae0ccea75070601f238c4f644783fe6c4e8183'),
    ('00000000-0000-4000-8000-000000000002'::uuid, 'user2@gomin.today', '로컬 사용자 2', 'scrypt$32768$8$3$ff25a17e96fc78b8ce98780db0c7bc17$60051d85e309a52efeda945a28908d19860a098c21deea062d2832e1dfb30d55'),
    ('00000000-0000-4000-8000-000000000003'::uuid, 'user3@gomin.today', '로컬 사용자 3', 'scrypt$32768$8$3$8db5efcb8167ad11adc45ec0f98e4924$44351f50c80c387351772a9c22f57afc1db4633bd98a1a3c17b8382d95ba74ff')
    on conflict (email) do nothing
    returning id
)
insert into public.member_consents(member_id,consent_type,version)
select created.id, consent_type, 'dev-2026-10-02'
from created cross join (values ('terms_of_service'),('privacy_collection')) as consents(consent_type)
on conflict do nothing;
