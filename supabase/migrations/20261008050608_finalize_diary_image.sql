create function public.finalize_diary_image(p_job_id uuid,p_lease_token uuid,
    p_title text,p_encouragement_text text,p_image_bucket text,p_image_object_key text)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_job public.generation_jobs%rowtype; v_result public.diary_results%rowtype;
        v_conversation_id uuid;
begin
    select conversation_id into v_conversation_id from public.generation_jobs where id=p_job_id and kind='image';
    if not found then raise exception 'Not found' using errcode='P0002'; end if;
    perform 1 from public.conversations where id=v_conversation_id for update;
    select * into v_job from public.generation_jobs where id=p_job_id for update;
    if v_job.status='succeeded' then
        select * into v_result from public.diary_results where generation_job_id=p_job_id;
        return to_jsonb(v_result);
    end if;
    if v_job.status <> 'running' or p_lease_token is null
       or v_job.lease_token is distinct from p_lease_token or v_job.lease_expires_at <= clock_timestamp() then
        raise exception 'Execution lease conflicts' using errcode='P0001';
    end if;
    insert into public.diary_results(member_id,summary_id,generation_job_id,title,encouragement_text,
        image_bucket,image_object_key)
      values(v_job.member_id,v_job.input_summary_id,v_job.id,p_title,p_encouragement_text,p_image_bucket,p_image_object_key)
      returning * into v_result;
    update public.generation_jobs set status='succeeded',finished_at=v_result.completed_at,
        lease_token=null,lease_expires_at=null where id=p_job_id;
    update public.conversations set phase='ready' where id=v_conversation_id and phase='generating'
      and not exists(select 1 from public.generation_jobs where conversation_id=v_conversation_id
        and status in ('queued','running'));
    return to_jsonb(v_result);
end;
$$;
revoke all on function public.finalize_diary_image(uuid,uuid,text,text,text,text) from public,anon,authenticated;
grant execute on function public.finalize_diary_image(uuid,uuid,text,text,text,text) to service_role;
