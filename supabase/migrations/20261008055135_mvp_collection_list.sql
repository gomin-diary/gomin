create function public.get_collection_entries(p_member_id uuid)
returns jsonb language sql stable security invoker set search_path = '' as $$
    select coalesce(jsonb_agg(to_jsonb(item) order by item.saved_at desc,item.id desc),'[]'::jsonb)
    from (
      select e.id,e.source_result_id,e.saved_at,r.title,r.diary_date,s.emotion_tags,
        r.image_bucket,r.image_object_key
      from public.collection_entries e
        join public.diary_results r on r.id=e.source_result_id and r.member_id=e.member_id
        join public.conversation_summaries s on s.id=r.summary_id and s.member_id=r.member_id
      where e.member_id=p_member_id
    ) item;
$$;
revoke all on function public.get_collection_entries(uuid) from public,anon,authenticated;
grant execute on function public.get_collection_entries(uuid) to service_role;
