-- Service-side uploads only. No anon/authenticated storage policy is added.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('gomin-diary-images', 'gomin-diary-images', false, 10485760,
        array['image/png', 'image/jpeg', 'image/webp'])
on conflict (id) do update
set public = false, file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
