create function public.list_collection_entries(p_member_id uuid,p_limit integer default 24,
    p_after_saved_at timestamptz default null,p_after_id uuid default null,p_emotion text default null)
returns jsonb language plpgsql stable security invoker set search_path = '' as $$
declare v_rows jsonb;
begin
    if p_limit is null or p_limit < 1 or p_limit > 100
       or (p_after_saved_at is null) <> (p_after_id is null) then
        raise exception 'Invalid pagination' using errcode='P0001';
    end if;
    select coalesce(jsonb_agg(to_jsonb(page) order by page.saved_at desc,page.id desc),'[]'::jsonb)
      into v_rows from (
        select e.id,e.source_result_id,e.saved_at,r.summary_id,s.conversation_id,
          r.title,r.diary_date,s.emotion_tags,r.image_bucket,r.image_object_key
        from public.collection_entries e join public.diary_results r on r.id=e.source_result_id and r.member_id=e.member_id
          join public.conversation_summaries s on s.id=r.summary_id and s.member_id=r.member_id
        where e.member_id=p_member_id
          and (p_after_saved_at is null or (e.saved_at,e.id) < (p_after_saved_at,p_after_id))
          and (p_emotion is null or p_emotion=any(s.emotion_tags))
        order by e.saved_at desc,e.id desc limit p_limit+1
      ) page;
    return v_rows;
end;
$$;
revoke all on function public.list_collection_entries(uuid,integer,timestamptz,uuid,text) from public,anon,authenticated;
grant execute on function public.list_collection_entries(uuid,integer,timestamptz,uuid,text) to service_role;
