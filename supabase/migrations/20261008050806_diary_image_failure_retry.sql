create function public.fail_diary_image(p_job_id uuid,p_lease_token uuid,p_error_code text)
returns boolean language plpgsql security invoker set search_path = '' as $$
declare v_job public.generation_jobs%rowtype; v_conversation_id uuid;
begin
    if p_error_code is null or p_error_code not in ('CONNECTION_FAILED','TIMEOUT','RATE_LIMITED',
      'PROVIDER_ERROR','INVALID_RESPONSE','RESPONSE_TOO_LARGE','INVALID_IMAGE','STORAGE_FAILED',
      'AI_NOT_CONFIGURED','INTERNAL_ERROR') then
        raise exception 'Invalid error code' using errcode='P0001';
    end if;
    select conversation_id into v_conversation_id from public.generation_jobs where id=p_job_id and kind='image';
    if not found then return false; end if;
    perform 1 from public.conversations where id=v_conversation_id for update;
    select * into v_job from public.generation_jobs where id=p_job_id for update;
    if v_job.status <> 'running' or p_lease_token is null or v_job.lease_token is distinct from p_lease_token
       or v_job.lease_expires_at <= clock_timestamp() then return false; end if;
    update public.generation_jobs set status='failed',finished_at=clock_timestamp(),error_code=p_error_code,
      lease_token=null,lease_expires_at=null where id=p_job_id;
    update public.conversations set phase='reviewing' where id=v_conversation_id and phase='generating'
      and not exists(select 1 from public.generation_jobs where conversation_id=v_conversation_id
        and status in ('queued','running'));
    return true;
end;
$$;

create function public.retry_diary_image(p_member_id uuid,p_job_id uuid)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_job public.generation_jobs%rowtype; v_conversation_id uuid;
begin
    select conversation_id into v_conversation_id from public.generation_jobs
      where id=p_job_id and member_id=p_member_id and kind='image';
    if not found then raise exception 'Not found' using errcode='P0002'; end if;
    perform 1 from public.conversations where id=v_conversation_id for update;
    select * into v_job from public.generation_jobs where id=p_job_id for update;
    if v_job.status='failed' then
        update public.generation_jobs set status='queued',error_code=null,finished_at=null,
          lease_token=null,lease_expires_at=null where id=p_job_id returning * into v_job;
        update public.conversations set phase='generating' where id=v_conversation_id;
    end if;
    return to_jsonb(v_job);
end;
$$;

create or replace function public.expire_diary_image_leases()
returns integer language plpgsql security invoker set search_path = '' as $$
declare v_conversation_id uuid; v_count integer := 0; v_changed integer;
begin
    for v_conversation_id in select distinct conversation_id from public.generation_jobs
      where kind='image' and status='running' and lease_expires_at <= clock_timestamp()
      order by conversation_id loop
        perform 1 from public.conversations where id=v_conversation_id for update;
        update public.generation_jobs set status='failed',error_code='LEASE_EXPIRED',
          finished_at=clock_timestamp(),lease_token=null,lease_expires_at=null
          where conversation_id=v_conversation_id and kind='image' and status='running'
            and lease_expires_at <= clock_timestamp();
        get diagnostics v_changed = row_count;
        v_count := v_count + v_changed;
        update public.conversations set phase='reviewing' where id=v_conversation_id and phase='generating'
          and not exists(select 1 from public.generation_jobs where conversation_id=v_conversation_id
            and status in ('queued','running'));
    end loop;
    return v_count;
end;
$$;
revoke all on function public.fail_diary_image(uuid,uuid,text),public.retry_diary_image(uuid,uuid)
  from public,anon,authenticated;
grant execute on function public.fail_diary_image(uuid,uuid,text),public.retry_diary_image(uuid,uuid)
  to service_role;
