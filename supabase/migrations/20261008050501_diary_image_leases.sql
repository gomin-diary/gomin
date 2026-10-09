create function public.claim_diary_image(p_job_id uuid default null, p_lease_seconds integer default 600)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_job public.generation_jobs%rowtype; v_inputs public.image_job_inputs%rowtype;
begin
    if p_lease_seconds is null or p_lease_seconds < 30 or p_lease_seconds > 1800 then
        raise exception 'Invalid lease duration' using errcode='P0001';
    end if;
    select j.* into v_job from public.generation_jobs j
      join public.image_job_inputs i on i.generation_job_id=j.id
      where j.kind='image' and j.status='queued' and (p_job_id is null or j.id=p_job_id)
      order by j.created_at,j.id for update of j skip locked limit 1;
    if not found then return null; end if;
    update public.generation_jobs set status='running',attempt_count=attempt_count+1,
      lease_token=gen_random_uuid(),lease_expires_at=clock_timestamp()+make_interval(secs=>p_lease_seconds)
      where id=v_job.id returning * into v_job;
    select * into v_inputs from public.image_job_inputs where generation_job_id=v_job.id;
    return to_jsonb(v_job) || jsonb_build_object('options',to_jsonb(v_inputs));
end;
$$;

-- A crashed/slow request may have been charged already. Expiry does not regenerate.
create function public.expire_diary_image_leases()
returns integer language plpgsql security invoker set search_path = '' as $$
declare v_count integer;
begin
    update public.generation_jobs set status='failed',error_code='LEASE_EXPIRED',
      finished_at=clock_timestamp(),lease_token=null,lease_expires_at=null
      where kind='image' and status='running' and lease_expires_at <= clock_timestamp();
    get diagnostics v_count = row_count;
    return v_count;
end;
$$;
revoke all on function public.claim_diary_image(uuid,integer),public.expire_diary_image_leases()
  from public,anon,authenticated;
grant execute on function public.claim_diary_image(uuid,integer),public.expire_diary_image_leases()
  to service_role;
