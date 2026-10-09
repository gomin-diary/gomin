create function public.get_collection_entry(p_member_id uuid,p_entry_id uuid)
returns jsonb language plpgsql stable security invoker set search_path = '' as $$
declare v_detail jsonb;
begin
    select to_jsonb(detail) into v_detail from (
      select e.id,e.source_result_id,e.saved_at,r.summary_id,s.conversation_id,r.title,r.diary_date,
        r.encouragement_text,r.completed_at,s.current_feeling,s.main_concerns,s.emotion_tags,
        r.image_bucket,r.image_object_key
      from public.collection_entries e
        join public.diary_results r on r.id=e.source_result_id and r.member_id=e.member_id
        join public.conversation_summaries s on s.id=r.summary_id and s.member_id=r.member_id
      where e.id=p_entry_id and e.member_id=p_member_id
    ) detail;
    if v_detail is null then raise exception 'Not found' using errcode='P0002'; end if;
    return v_detail;
end;
$$;
revoke all on function public.get_collection_entry(uuid,uuid) from public,anon,authenticated;
grant execute on function public.get_collection_entry(uuid,uuid) to service_role;
