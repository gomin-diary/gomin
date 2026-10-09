-- Preserve applied migration history and existing records; image requests now run inline.
drop function public.submit_diary_image(uuid,uuid,uuid,uuid,text,text,text,text);
drop function public.claim_diary_image(uuid,integer);
drop function public.expire_diary_image_leases();
drop function public.finalize_diary_image(uuid,uuid,text,text,text,text);
drop function public.fail_diary_image(uuid,uuid,text);
drop function public.retry_diary_image(uuid,uuid);
drop function public.get_diary_image_job(uuid,uuid);
drop function public.list_collection_entries(uuid,integer,timestamptz,uuid,text);
revoke all on public.image_job_inputs from service_role;

-- Historical job-linked results remain valid; new results need no image job.
alter table public.diary_results alter column generation_job_id drop not null;

create function public.prepare_diary_summary(p_member_id uuid,p_summary_id uuid)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_summary public.conversation_summaries%rowtype;
begin
    select * into v_summary from public.conversation_summaries
      where id=p_summary_id and member_id=p_member_id;
    if not found then raise exception 'Not found' using errcode='P0002'; end if;
    -- The existing confirmation trigger rejects a stale, unconfirmed summary.
    update public.conversation_summaries set confirmed_at=clock_timestamp()
      where id=p_summary_id and confirmed_at is null;
    return to_jsonb(v_summary);
end;
$$;

create function public.create_diary_result(p_member_id uuid,p_summary_id uuid,
    p_title text,p_encouragement_text text,p_image_bucket text,p_image_object_key text)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_result public.diary_results%rowtype;
begin
    perform 1 from public.conversation_summaries
      where id=p_summary_id and member_id=p_member_id and confirmed_at is not null;
    if not found then raise exception 'Not found' using errcode='P0002'; end if;
    insert into public.diary_results(member_id,summary_id,title,encouragement_text,
      image_bucket,image_object_key) values(p_member_id,p_summary_id,p_title,
      p_encouragement_text,p_image_bucket,p_image_object_key) returning * into v_result;
    return to_jsonb(v_result);
end;
$$;
revoke all on function public.prepare_diary_summary(uuid,uuid),
    public.create_diary_result(uuid,uuid,text,text,text,text) from public,anon,authenticated;
grant execute on function public.prepare_diary_summary(uuid,uuid),
    public.create_diary_result(uuid,uuid,text,text,text,text) to service_role;
