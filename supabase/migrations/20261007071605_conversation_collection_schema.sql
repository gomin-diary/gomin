-- GOMIN-74: conversation, AI-generation and collection schema.
-- No data migration, Storage bucket creation, deletion or retention scheduler.
-- The backend still owns session authorization, transactional command RPCs,
-- sequence/version allocation and conditional lease-token completion updates.

create function public.gomin_nonblank_text_array(p_values text[])
returns boolean language sql immutable parallel safe security invoker
set search_path = '' as $$
    select p_values is not null
        and coalesce(array_ndims(p_values), 1) = 1
        and not exists (
            select 1 from unnest(p_values) as item
            where item is null or item !~ '[^[:space:]]'
        );
$$;

create table public.conversations (
    id uuid primary key default gen_random_uuid(),
    member_id uuid not null references public.members(id) on delete restrict,
    phase text not null default 'chatting'
        check (phase in ('chatting', 'summarizing', 'reviewing', 'generating', 'ready')),
    next_seq_no bigint not null default 1 check (next_seq_no > 0),
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    unique (member_id, id)
);

create table public.conversation_messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.conversations(id) on delete restrict,
    seq_no bigint not null check (seq_no > 0),
    role text not null check (role in ('user', 'assistant')),
    content text not null check (content ~ '[^[:space:]]'),
    client_message_id uuid,
    generation_job_id uuid unique,
    created_at timestamptz not null default clock_timestamp(),
    unique (conversation_id, id),
    unique (conversation_id, seq_no),
    unique (conversation_id, client_message_id),
    check (
        (role = 'user' and client_message_id is not null and generation_job_id is null)
        or (role = 'assistant' and client_message_id is null and generation_job_id is not null)
    )
);

create table public.generation_jobs (
    id uuid primary key default gen_random_uuid(),
    member_id uuid not null,
    conversation_id uuid not null,
    kind text not null check (kind in ('reply', 'summary', 'image')),
    input_message_id uuid,
    input_summary_id uuid,
    source_until_seq_no bigint check (source_until_seq_no > 0),
    idempotency_key uuid not null,
    request_fingerprint text not null check (request_fingerprint ~ '[^[:space:]]'),
    status text not null default 'queued' check (status in ('queued', 'running', 'succeeded', 'failed')),
    attempt_count integer not null default 0 check (attempt_count >= 0),
    lease_token uuid,
    lease_expires_at timestamptz,
    error_code text check (error_code ~ '[^[:space:]]'),
    created_at timestamptz not null default clock_timestamp(),
    finished_at timestamptz,
    unique (member_id, id),
    unique (conversation_id, id),
    unique (member_id, conversation_id, id),
    unique (id, input_summary_id),
    unique (member_id, idempotency_key),
    foreign key (member_id, conversation_id)
        references public.conversations(member_id, id) on delete restrict,
    foreign key (conversation_id, input_message_id)
        references public.conversation_messages(conversation_id, id) on delete restrict,
    foreign key (conversation_id, source_until_seq_no)
        references public.conversation_messages(conversation_id, seq_no) on delete restrict,
    check (
        (kind = 'reply' and input_message_id is not null
            and input_summary_id is null and source_until_seq_no is not null)
        or (kind = 'summary' and input_message_id is null
            and input_summary_id is null and source_until_seq_no is not null)
        or (kind = 'image' and input_message_id is null
            and input_summary_id is not null and source_until_seq_no is null)
    ),
    check (
        (status = 'queued' and lease_token is null and lease_expires_at is null
            and finished_at is null and error_code is null)
        or (status = 'running' and lease_token is not null and lease_expires_at is not null
            and attempt_count > 0 and finished_at is null and error_code is null)
        or (status = 'succeeded' and lease_token is null and lease_expires_at is null
            and finished_at is not null and error_code is null)
        or (status = 'failed' and lease_token is null and lease_expires_at is null
            and finished_at is not null and error_code is not null)
    )
);
create unique index generation_jobs_reply_input_key
    on public.generation_jobs(input_message_id) where kind = 'reply';

create table public.conversation_summaries (
    id uuid primary key default gen_random_uuid(),
    member_id uuid not null,
    conversation_id uuid not null,
    version integer not null check (version > 0),
    source_until_seq_no bigint not null check (source_until_seq_no > 0),
    current_feeling text not null check (current_feeling ~ '[^[:space:]]'),
    main_concerns text[] not null check (public.gomin_nonblank_text_array(main_concerns)),
    emotion_tags text[] not null check (public.gomin_nonblank_text_array(emotion_tags)),
    generation_job_id uuid not null unique,
    confirmed_at timestamptz,
    created_at timestamptz not null default clock_timestamp(),
    unique (member_id, id),
    unique (member_id, conversation_id, id),
    unique (conversation_id, version),
    foreign key (member_id, conversation_id)
        references public.conversations(member_id, id) on delete restrict,
    foreign key (conversation_id, source_until_seq_no)
        references public.conversation_messages(conversation_id, seq_no) on delete restrict,
    foreign key (member_id, conversation_id, generation_job_id)
        references public.generation_jobs(member_id, conversation_id, id) on delete restrict
);

-- Resolve the cycles only after their target tables exist.
alter table public.generation_jobs
    add constraint generation_jobs_input_summary_fkey
    foreign key (member_id, conversation_id, input_summary_id)
        references public.conversation_summaries(member_id, conversation_id, id) on delete restrict;
alter table public.conversation_messages
    add constraint conversation_messages_generation_job_fkey
    foreign key (conversation_id, generation_job_id)
        references public.generation_jobs(conversation_id, id) on delete restrict;

create table public.diary_results (
    id uuid primary key default gen_random_uuid(),
    member_id uuid not null,
    summary_id uuid not null,
    generation_job_id uuid not null unique,
    title text not null check (title ~ '[^[:space:]]'),
    encouragement_text text not null check (encouragement_text ~ '[^[:space:]]'),
    completed_at timestamptz not null default clock_timestamp(),
    diary_date date generated always as ((completed_at at time zone 'Asia/Seoul')::date) stored not null,
    image_bucket text not null check (image_bucket ~ '[^[:space:]]'),
    image_object_key text not null check (image_object_key ~ '[^[:space:]]'),
    unique (member_id, id),
    unique (image_bucket, image_object_key),
    foreign key (member_id, summary_id)
        references public.conversation_summaries(member_id, id) on delete restrict,
    foreign key (member_id, generation_job_id)
        references public.generation_jobs(member_id, id) on delete restrict,
    -- Also guarantees an image-kind job: only image jobs have an input summary.
    foreign key (generation_job_id, summary_id)
        references public.generation_jobs(id, input_summary_id) on delete restrict
);

create table public.collection_entries (
    id uuid primary key default gen_random_uuid(),
    member_id uuid not null,
    source_result_id uuid not null unique,
    saved_at timestamptz not null default clock_timestamp(),
    foreign key (member_id, source_result_id)
        references public.diary_results(member_id, id) on delete restrict
);

-- Existing composite UNIQUE indexes support message order and latest-summary scans.
create index conversations_member_updated_idx
    on public.conversations(member_id, updated_at desc, id desc);
create index generation_jobs_conversation_created_idx
    on public.generation_jobs(conversation_id, created_at desc);
create index generation_jobs_input_summary_idx
    on public.generation_jobs(input_summary_id) where input_summary_id is not null;
create index collection_entries_member_saved_idx
    on public.collection_entries(member_id, saved_at desc, id desc);

create function public.gomin_conversation_touch()
returns trigger language plpgsql security invoker set search_path = '' as $$
begin
    if (new.id, new.member_id, new.created_at) is distinct from
       (old.id, old.member_id, old.created_at) or new.next_seq_no < old.next_seq_no then
        raise exception 'Conversation identity and sequence cannot move backwards' using errcode = '23514';
    end if;
    new.updated_at := clock_timestamp();
    return new;
end;
$$;
create trigger conversations_touch before update on public.conversations
    for each row execute function public.gomin_conversation_touch();

create function public.gomin_validate_message()
returns trigger language plpgsql security invoker set search_path = '' as $$
declare v_kind text;
begin
    if tg_op = 'UPDATE' and new is distinct from old then
        raise exception 'Messages are immutable' using errcode = '23514';
    end if;
    -- Serialize message writes against summary confirmation.
    perform 1 from public.conversations where id = new.conversation_id for update;
    if new.role = 'assistant' and new.generation_job_id is not null then
        select kind into v_kind from public.generation_jobs where id = new.generation_job_id;
        if v_kind is distinct from 'reply' then
            raise exception 'Assistant output requires a reply job' using errcode = '23514';
        end if;
    end if;
    return new;
end;
$$;
create trigger conversation_messages_validate before insert or update on public.conversation_messages
    for each row execute function public.gomin_validate_message();

create function public.gomin_validate_generation_job()
returns trigger language plpgsql security invoker set search_path = '' as $$
declare v_role text; v_seq bigint; v_confirmed_at timestamptz;
begin
    if tg_op = 'UPDATE' then
        if (new.id, new.member_id, new.conversation_id, new.kind, new.input_message_id,
            new.input_summary_id, new.source_until_seq_no, new.idempotency_key,
            new.request_fingerprint, new.created_at) is distinct from
           (old.id, old.member_id, old.conversation_id, old.kind, old.input_message_id,
            old.input_summary_id, old.source_until_seq_no, old.idempotency_key,
            old.request_fingerprint, old.created_at) then
            raise exception 'Generation job inputs are immutable' using errcode = '23514';
        end if;
        if old.status = 'succeeded' and new is distinct from old then
            raise exception 'Successful generation jobs are immutable' using errcode = '23514';
        end if;
    end if;
    if new.kind = 'reply' and new.input_message_id is not null then
        select role, seq_no into v_role, v_seq
            from public.conversation_messages where id = new.input_message_id;
        if v_role is distinct from 'user' or v_seq is distinct from new.source_until_seq_no then
            raise exception 'Reply input must match its user message boundary' using errcode = '23514';
        end if;
    elsif new.kind = 'image' and new.input_summary_id is not null then
        select confirmed_at into v_confirmed_at
            from public.conversation_summaries where id = new.input_summary_id for key share;
        if v_confirmed_at is null then
            raise exception 'Image input must be a confirmed summary' using errcode = '23514';
        end if;
    end if;
    return new;
end;
$$;
create trigger generation_jobs_validate before insert or update on public.generation_jobs
    for each row execute function public.gomin_validate_generation_job();

create function public.gomin_validate_summary()
returns trigger language plpgsql security invoker set search_path = '' as $$
declare v_kind text; v_boundary bigint; v_latest_version integer; v_latest_seq bigint;
begin
    perform 1 from public.conversations where id = new.conversation_id for update;
    if tg_op = 'UPDATE' then
        if (to_jsonb(new) - 'confirmed_at') is distinct from (to_jsonb(old) - 'confirmed_at')
           or (old.confirmed_at is not null and new.confirmed_at is distinct from old.confirmed_at) then
            raise exception 'Summary content and its first confirmation are immutable' using errcode = '23514';
        end if;
        if old.confirmed_at is null and new.confirmed_at is not null then
            select max(version) into v_latest_version from public.conversation_summaries
                where conversation_id = new.conversation_id;
            select max(seq_no) into v_latest_seq from public.conversation_messages
                where conversation_id = new.conversation_id;
            if new.version is distinct from v_latest_version
               or new.source_until_seq_no is distinct from v_latest_seq then
                raise exception 'Only the current summary can be confirmed' using errcode = '23514';
            end if;
        end if;
    elsif new.confirmed_at is not null then
        raise exception 'Create a summary before confirming it' using errcode = '23514';
    end if;
    select kind, source_until_seq_no into v_kind, v_boundary
        from public.generation_jobs where id = new.generation_job_id;
    if v_kind is distinct from 'summary' or v_boundary is distinct from new.source_until_seq_no then
        raise exception 'Summary output must match its summary job boundary' using errcode = '23514';
    end if;
    return new;
end;
$$;
create trigger conversation_summaries_validate before insert or update on public.conversation_summaries
    for each row execute function public.gomin_validate_summary();

create function public.gomin_immutable_record()
returns trigger language plpgsql security invoker set search_path = '' as $$
begin
    if new is distinct from old then
        raise exception 'Completed results and collection entries are immutable' using errcode = '23514';
    end if;
    return new;
end;
$$;
create trigger diary_results_immutable before update on public.diary_results
    for each row execute function public.gomin_immutable_record();
create trigger collection_entries_immutable before update on public.collection_entries
    for each row execute function public.gomin_immutable_record();

-- Check final transaction state, allowing output INSERT and status UPDATE in either order.
create function public.gomin_validate_generation_output()
returns trigger language plpgsql security invoker set search_path = '' as $$
declare v_id uuid; v_job public.generation_jobs%rowtype; v_has_output boolean;
begin
    if tg_table_name = 'generation_jobs' then v_id := new.id;
    else v_id := new.generation_job_id;
    end if;
    if v_id is null then return null; end if;
    select * into v_job from public.generation_jobs where id = v_id for update;
    if not found then return null; end if;
    case v_job.kind
        when 'reply' then
            select exists(select 1 from public.conversation_messages where generation_job_id = v_id) into v_has_output;
        when 'summary' then
            select exists(select 1 from public.conversation_summaries where generation_job_id = v_id) into v_has_output;
        when 'image' then
            select exists(select 1 from public.diary_results where generation_job_id = v_id) into v_has_output;
    end case;
    if (v_job.status = 'succeeded') is distinct from v_has_output then
        raise exception 'A successful generation job and its output must commit together' using errcode = '23514';
    end if;
    return null;
end;
$$;
create constraint trigger generation_jobs_output_consistency
    after insert or update on public.generation_jobs deferrable initially deferred
    for each row execute function public.gomin_validate_generation_output();
create constraint trigger conversation_messages_output_consistency
    after insert or update on public.conversation_messages deferrable initially deferred
    for each row execute function public.gomin_validate_generation_output();
create constraint trigger conversation_summaries_output_consistency
    after insert or update on public.conversation_summaries deferrable initially deferred
    for each row execute function public.gomin_validate_generation_output();
create constraint trigger diary_results_output_consistency
    after insert or update on public.diary_results deferrable initially deferred
    for each row execute function public.gomin_validate_generation_output();

alter table public.conversations enable row level security;
alter table public.conversation_messages enable row level security;
alter table public.conversation_summaries enable row level security;
alter table public.generation_jobs enable row level security;
alter table public.diary_results enable row level security;
alter table public.collection_entries enable row level security;

-- Explicitly clear default privileges, including any inherited service-role DELETE grants.
revoke all on public.conversations, public.conversation_messages, public.conversation_summaries,
    public.generation_jobs, public.diary_results, public.collection_entries
    from public, anon, authenticated, service_role;
grant select, insert on public.conversations, public.conversation_messages, public.conversation_summaries,
    public.generation_jobs, public.diary_results, public.collection_entries to service_role;
grant update on public.conversations, public.generation_jobs to service_role;
grant update (confirmed_at) on public.conversation_summaries to service_role;
revoke all on function public.gomin_nonblank_text_array(text[]),
    public.gomin_conversation_touch(), public.gomin_validate_message(),
    public.gomin_validate_generation_job(), public.gomin_validate_summary(),
    public.gomin_immutable_record(), public.gomin_validate_generation_output()
    from public, anon, authenticated, service_role;
grant execute on function public.gomin_nonblank_text_array(text[]) to service_role;

comment on table public.diary_results is 'Completed results remain indefinitely, including unsaved results.';
comment on column public.diary_results.diary_date is 'Generated Korean calendar date of completed_at (Asia/Seoul).';
comment on table public.collection_entries is 'Saving is separate from generation. Deletion is outside the MVP.';
