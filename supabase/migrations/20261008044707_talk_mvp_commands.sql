-- GOMIN-69: atomic conversation commands. Existing schema/IDs stay intact.
-- Invoker functions are callable only by service_role; member ID comes from
-- require_member, never from a browser payload. No retry worker or image flow.

create function public.gomin_talk_lock(p_member_id uuid, p_conversation_id uuid)
returns void language plpgsql security invoker set search_path = '' as $$
begin
    perform 1 from public.conversations
        where id = p_conversation_id and member_id = p_member_id for update;
    if not found then raise exception 'TALK_NOT_FOUND' using errcode = 'P0002'; end if;
    -- Expiration ends an abandoned execution; it never requeues or retries it.
    update public.generation_jobs set status = 'failed', error_code = 'AI_TIMEOUT',
        finished_at = clock_timestamp(), lease_token = null, lease_expires_at = null
        where conversation_id = p_conversation_id and kind in ('reply', 'summary')
            and status = 'running' and lease_expires_at <= clock_timestamp();
end;
$$;

create function public.gomin_talk_snapshot(p_member_id uuid, p_conversation_id uuid)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_conversation public.conversations%rowtype;
begin
    -- Read only: an expired job is projected as failed, never restarted.
    select * into v_conversation from public.conversations
        where id = p_conversation_id and member_id = p_member_id;
    if not found then raise exception 'TALK_NOT_FOUND' using errcode = 'P0002'; end if;
    return jsonb_build_object('id', v_conversation.id, 'phase', v_conversation.phase,
        'messages', coalesce((select jsonb_agg(to_jsonb(m) order by m.seq_no)
            from public.conversation_messages m where m.conversation_id = p_conversation_id), '[]'::jsonb),
        'summaries', coalesce((select jsonb_agg(to_jsonb(s) order by s.version)
            from public.conversation_summaries s where s.conversation_id = p_conversation_id
                and s.member_id = p_member_id), '[]'::jsonb),
        'jobs', coalesce((select jsonb_agg(jsonb_build_object('id', j.id, 'kind', j.kind,
            'status', case when j.status = 'running' and j.lease_expires_at <= clock_timestamp()
                then 'failed' else j.status end, 'source_until_seq_no', j.source_until_seq_no,
            'error_code', case when j.status = 'running' and j.lease_expires_at <= clock_timestamp()
                then 'AI_TIMEOUT' else j.error_code end) order by j.created_at, j.id)
            from public.generation_jobs j where j.conversation_id = p_conversation_id
                and j.member_id = p_member_id and j.kind in ('reply', 'summary')), '[]'::jsonb));
end;
$$;

create function public.gomin_talk_send(p_member_id uuid, p_conversation_id uuid,
    p_client_message_id uuid, p_content text)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_message public.conversation_messages%rowtype; v_job public.generation_jobs%rowtype;
    v_seq bigint; v_phase text;
begin
    perform public.gomin_talk_lock(p_member_id, p_conversation_id);
    if p_content is null or char_length(p_content) > 100 or p_content !~ '[^[:space:]]' then
        raise exception 'TALK_INVALID_INPUT' using errcode = '22023';
    end if;
    select * into v_message from public.conversation_messages
        where conversation_id = p_conversation_id and client_message_id = p_client_message_id;
    if found then
        if v_message.content is distinct from p_content then
            raise exception 'TALK_CONFLICT' using errcode = 'P0001';
        end if;
        select * into v_job from public.generation_jobs where input_message_id = v_message.id and kind = 'reply';
        return jsonb_build_object('message', to_jsonb(v_message), 'job', to_jsonb(v_job), 'execute', false);
    end if;
    select phase, next_seq_no into v_phase, v_seq from public.conversations where id = p_conversation_id;
    if v_phase <> 'chatting' or exists(select 1 from public.generation_jobs
        where conversation_id = p_conversation_id and kind in ('reply', 'summary') and status = 'running') then
        raise exception 'TALK_BUSY' using errcode = 'P0001';
    end if;
    insert into public.conversation_messages(conversation_id, seq_no, role, content, client_message_id)
        values(p_conversation_id, v_seq, 'user', p_content, p_client_message_id) returning * into v_message;
    insert into public.generation_jobs(member_id, conversation_id, kind, input_message_id,
        source_until_seq_no, idempotency_key, request_fingerprint, status, attempt_count, lease_token, lease_expires_at)
        values(p_member_id, p_conversation_id, 'reply', v_message.id, v_seq, gen_random_uuid(),
            v_message.id::text, 'running', 1, gen_random_uuid(), clock_timestamp() + interval '90 seconds')
        returning * into v_job;
    update public.conversations set next_seq_no = v_seq + 1 where id = p_conversation_id;
    return jsonb_build_object('message', to_jsonb(v_message), 'job', to_jsonb(v_job), 'execute', true);
end;
$$;

create function public.gomin_talk_start_summary(p_member_id uuid, p_conversation_id uuid, p_request_id uuid)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_job public.generation_jobs%rowtype; v_boundary bigint;
begin
    perform public.gomin_talk_lock(p_member_id, p_conversation_id);
    select * into v_job from public.generation_jobs where member_id = p_member_id and idempotency_key = p_request_id;
    if found then
        if v_job.conversation_id <> p_conversation_id or v_job.kind <> 'summary' then
            raise exception 'TALK_CONFLICT' using errcode = 'P0001';
        end if;
        return jsonb_build_object('job', to_jsonb(v_job), 'execute', false);
    end if;
    if not exists(select 1 from public.conversation_messages
        where conversation_id = p_conversation_id and role = 'user') then
        raise exception 'TALK_EMPTY' using errcode = 'P0001';
    end if;
    if exists(select 1 from public.generation_jobs where conversation_id = p_conversation_id
        and kind in ('reply', 'summary') and status = 'running') then
        raise exception 'TALK_BUSY' using errcode = 'P0001';
    end if;
    select max(seq_no) into v_boundary from public.conversation_messages where conversation_id = p_conversation_id;
    insert into public.generation_jobs(member_id, conversation_id, kind, source_until_seq_no,
        idempotency_key, request_fingerprint, status, attempt_count, lease_token, lease_expires_at)
        values(p_member_id, p_conversation_id, 'summary', v_boundary, p_request_id, v_boundary::text,
            'running', 1, gen_random_uuid(), clock_timestamp() + interval '90 seconds') returning * into v_job;
    update public.conversations set phase = 'summarizing' where id = p_conversation_id;
    return jsonb_build_object('job', to_jsonb(v_job), 'execute', true);
end;
$$;

create function public.gomin_talk_complete(p_member_id uuid, p_conversation_id uuid,
    p_job_id uuid, p_lease_token uuid, p_output jsonb, p_error_code text default null)
returns boolean language plpgsql security invoker set search_path = '' as $$
declare v_job public.generation_jobs%rowtype; v_seq bigint; v_version integer;
begin
    perform public.gomin_talk_lock(p_member_id, p_conversation_id);
    select * into v_job from public.generation_jobs where id = p_job_id
        and member_id = p_member_id and conversation_id = p_conversation_id and kind in ('reply', 'summary') for update;
    if not found or v_job.status <> 'running' or v_job.lease_token is distinct from p_lease_token then return false; end if;
    if p_error_code is not null then
        update public.generation_jobs set status = 'failed', error_code = p_error_code,
            finished_at = clock_timestamp(), lease_token = null, lease_expires_at = null where id = p_job_id;
        return true;
    end if;
    if v_job.kind = 'reply' then
        select next_seq_no into v_seq from public.conversations where id = p_conversation_id;
        insert into public.conversation_messages(conversation_id, seq_no, role, content, generation_job_id)
            values(p_conversation_id, v_seq, 'assistant', p_output->>'content', p_job_id);
        update public.conversations set next_seq_no = v_seq + 1 where id = p_conversation_id;
    else
        select coalesce(max(version), 0) + 1 into v_version from public.conversation_summaries where conversation_id = p_conversation_id;
        insert into public.conversation_summaries(member_id, conversation_id, version, source_until_seq_no,
            current_feeling, main_concerns, emotion_tags, generation_job_id)
            values(p_member_id, p_conversation_id, v_version, v_job.source_until_seq_no,
                p_output->>'current_feeling', array(select jsonb_array_elements_text(p_output->'main_concerns')),
                array(select jsonb_array_elements_text(p_output->'emotion_tags')), p_job_id);
        update public.conversations set phase = 'reviewing' where id = p_conversation_id;
    end if;
    update public.generation_jobs set status = 'succeeded', finished_at = clock_timestamp(),
        lease_token = null, lease_expires_at = null where id = p_job_id;
    return true;
end;
$$;

create function public.gomin_talk_resume(p_member_id uuid, p_conversation_id uuid)
returns void language plpgsql security invoker set search_path = '' as $$
begin
    perform public.gomin_talk_lock(p_member_id, p_conversation_id);
    if exists(select 1 from public.generation_jobs where conversation_id = p_conversation_id
        and kind = 'summary' and status = 'running') then
        raise exception 'TALK_BUSY' using errcode = 'P0001';
    end if;
    update public.conversations set phase = 'chatting' where id = p_conversation_id;
end;
$$;

create function public.gomin_talk_confirm(p_member_id uuid, p_conversation_id uuid, p_summary_id uuid)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_summary public.conversation_summaries%rowtype;
begin
    perform public.gomin_talk_lock(p_member_id, p_conversation_id);
    select * into v_summary from public.conversation_summaries where id = p_summary_id
        and conversation_id = p_conversation_id and member_id = p_member_id;
    if not found then raise exception 'TALK_NOT_FOUND' using errcode = 'P0002'; end if;
    if exists(select 1 from public.generation_jobs where conversation_id = p_conversation_id
        and kind in ('reply', 'summary') and status = 'running')
        or v_summary.version <> (select max(version) from public.conversation_summaries where conversation_id = p_conversation_id)
        or v_summary.source_until_seq_no <> (select max(seq_no) from public.conversation_messages where conversation_id = p_conversation_id) then
        raise exception 'TALK_STALE_SUMMARY' using errcode = 'P0001';
    end if;
    update public.conversation_summaries set confirmed_at = coalesce(confirmed_at, clock_timestamp())
        where id = p_summary_id returning * into v_summary;
    -- reviewing remains: confirmation alone never starts an image job.
    return to_jsonb(v_summary);
end;
$$;

revoke all on function public.gomin_talk_lock(uuid,uuid), public.gomin_talk_snapshot(uuid,uuid),
    public.gomin_talk_send(uuid,uuid,uuid,text), public.gomin_talk_start_summary(uuid,uuid,uuid),
    public.gomin_talk_complete(uuid,uuid,uuid,uuid,jsonb,text), public.gomin_talk_resume(uuid,uuid),
    public.gomin_talk_confirm(uuid,uuid,uuid) from public, anon, authenticated, service_role;
grant execute on function public.gomin_talk_lock(uuid,uuid), public.gomin_talk_snapshot(uuid,uuid),
    public.gomin_talk_send(uuid,uuid,uuid,text), public.gomin_talk_start_summary(uuid,uuid,uuid),
    public.gomin_talk_complete(uuid,uuid,uuid,uuid,jsonb,text), public.gomin_talk_resume(uuid,uuid),
    public.gomin_talk_confirm(uuid,uuid,uuid) to service_role;
