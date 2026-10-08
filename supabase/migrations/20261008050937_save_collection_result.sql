create function public.save_collection_result(p_member_id uuid,p_result_id uuid)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare v_entry public.collection_entries%rowtype;
begin
    perform 1 from public.diary_results where id=p_result_id and member_id=p_member_id;
    if not found then raise exception 'Not found' using errcode='P0002'; end if;
    -- DO NOTHING never rewrites the original saved_at and needs no UPDATE grant.
    insert into public.collection_entries(member_id,source_result_id)
      values(p_member_id,p_result_id) on conflict(source_result_id) do nothing;
    select * into v_entry from public.collection_entries
      where source_result_id=p_result_id and member_id=p_member_id;
    if not found then raise exception 'Not found' using errcode='P0002'; end if;
    return to_jsonb(v_entry);
end;
$$;
revoke all on function public.save_collection_result(uuid,uuid) from public,anon,authenticated;
grant execute on function public.save_collection_result(uuid,uuid) to service_role;
