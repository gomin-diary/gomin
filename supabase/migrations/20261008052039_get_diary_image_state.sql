create function public.get_diary_result(p_member_id uuid,p_result_id uuid)
returns jsonb language plpgsql stable security invoker set search_path = '' as $$
declare v_result jsonb;
begin
    select to_jsonb(detail) into v_result from (
      select r.id,r.generation_job_id,r.summary_id,s.conversation_id,r.title,r.diary_date,r.completed_at,
        r.encouragement_text,s.current_feeling,s.main_concerns,s.emotion_tags,
        r.image_bucket,r.image_object_key,e.id as collection_entry_id,e.saved_at
      from public.diary_results r join public.conversation_summaries s on s.id=r.summary_id and s.member_id=r.member_id
        left join public.collection_entries e on e.source_result_id=r.id and e.member_id=r.member_id
      where r.id=p_result_id and r.member_id=p_member_id
    ) detail;
    if v_result is null then raise exception 'Not found' using errcode='P0002'; end if;
    return v_result;
end;
$$;
create function public.get_diary_image_job(p_member_id uuid,p_job_id uuid)
returns jsonb language plpgsql stable security invoker set search_path = '' as $$
declare v_job public.generation_jobs%rowtype; v_result_id uuid; v_result jsonb := null;
begin
    select * into v_job from public.generation_jobs where id=p_job_id and member_id=p_member_id and kind='image';
    if not found then raise exception 'Not found' using errcode='P0002'; end if;
    if v_job.status='succeeded' then
        select id into v_result_id from public.diary_results where generation_job_id=p_job_id;
        v_result := public.get_diary_result(p_member_id,v_result_id);
    end if;
    return to_jsonb(v_job) || jsonb_build_object('result',v_result);
end;
$$;
revoke all on function public.get_diary_result(uuid,uuid),public.get_diary_image_job(uuid,uuid)
    from public,anon,authenticated;
grant execute on function public.get_diary_result(uuid,uuid),public.get_diary_image_job(uuid,uuid) to service_role;
