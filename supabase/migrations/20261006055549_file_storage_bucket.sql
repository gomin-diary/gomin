-- URL issuance uses the backend service key. Do not grant general browser access.
-- Storage enforces this limit on actual bytes, including signed uploads.
insert into storage.buckets (id, name, public, file_size_limit)
values ('gomin-files', 'gomin-files', false, 10485760)
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit;
