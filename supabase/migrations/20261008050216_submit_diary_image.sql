-- Persist the exact model/options for durable execution after process restarts.
create table public.image_job_inputs (
    generation_job_id uuid primary key references public.generation_jobs(id) on delete restrict,
    text_model text not null check (text_model ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]*$'),
    image_model text not null check (image_model ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]*$'),
    image_size text not null check (image_size ~ '^[1-9][0-9]{0,3}x[1-9][0-9]{0,3}$'),
    prompt_version text not null check (prompt_version = 'diary-v1')
);
create trigger image_job_inputs_immutable before update on public.image_job_inputs
    for each row execute function public.gomin_immutable_record();
alter table public.image_job_inputs enable row level security;
revoke all on public.image_job_inputs from public, anon, authenticated, service_role;
grant select, insert on public.image_job_inputs to service_role;

create function public.submit_diary_image(
    p_member_id uuid, p_conversation_id uuid, p_summary_id uuid,
    p_idempotency_key uuid, p_fingerprint text, p_text_model text,
    p_image_model text, p_image_size text
) returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_job public.generation_jobs%rowtype; v_summary public.conversation_summaries%rowtype;
begin
    -- One member/key may arrive on different conversations at the same time.
    perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        p_member_id::text || ':' || p_idempotency_key::text, 0));
    select * into v_job from public.generation_jobs
        where member_id=p_member_id and idempotency_key=p_idempotency_key;
    if found then
        if v_job.kind <> 'image' or v_job.conversation_id <> p_conversation_id
           or v_job.input_summary_id <> p_summary_id or v_job.request_fingerprint <> p_fingerprint then
            raise exception 'Request key conflicts' using errcode='P0001';
        end if;
        return to_jsonb(v_job);
    end if;
    perform 1 from public.conversations where id=p_conversation_id and member_id=p_member_id for update;
    if not found then raise exception 'Not found' using errcode='P0002'; end if;
    select * into v_summary from public.conversation_summaries
        where id=p_summary_id and member_id=p_member_id and conversation_id=p_conversation_id;
    if not found then raise exception 'Not found' using errcode='P0002'; end if;
    if v_summary.version is distinct from (select max(version) from public.conversation_summaries
          where conversation_id=p_conversation_id)
       or v_summary.source_until_seq_no is distinct from (select max(seq_no) from public.conversation_messages
          where conversation_id=p_conversation_id) then
        raise exception 'Summary is stale' using errcode='P0001';
    end if;
    if v_summary.confirmed_at is null then
        update public.conversation_summaries set confirmed_at=clock_timestamp() where id=p_summary_id;
    end if;
    insert into public.generation_jobs(member_id,conversation_id,kind,input_summary_id,
        idempotency_key,request_fingerprint)
    values(p_member_id,p_conversation_id,'image',p_summary_id,p_idempotency_key,p_fingerprint)
    returning * into v_job;
    insert into public.image_job_inputs values(v_job.id,p_text_model,p_image_model,p_image_size,'diary-v1');
    update public.conversations set phase='generating' where id=p_conversation_id;
    return to_jsonb(v_job);
end;
$$;
revoke all on function public.submit_diary_image(uuid,uuid,uuid,uuid,text,text,text,text)
    from public, anon, authenticated;
grant execute on function public.submit_diary_image(uuid,uuid,uuid,uuid,text,text,text,text) to service_role;
