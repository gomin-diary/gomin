-- Local development only. Adds one summary per documented test account.
-- Keep existing fixtures and generated/saved diaries unchanged on repeated runs.
do $$
declare fixture record; member_uuid uuid; suffix text;
    conversation_uuid uuid; message_uuid uuid; job_uuid uuid; summary_uuid uuid;
begin
    for fixture in select * from (values
      (1,'user1@gomin.today','새로운 일을 시작하며 기대와 불안이 함께 느껴져요.',
        array['새로운 업무에 잘 적응할 수 있을지 걱정돼요.','조급해하지 않고 나만의 속도를 찾고 싶어요.'],array['불안','일상']),
      (2,'user2@gomin.today','친구와 마음을 나눈 뒤 한결 편안하고 기뻐요.',
        array['바쁜 일상에서도 소중한 관계를 잘 이어가고 싶어요.'],array['기쁨','관계']),
      (3,'user3@gomin.today','하루가 뜻대로 풀리지 않아 조금 지치고 속상해요.',
        array['실수에 너무 오래 마음을 쓰지 않고 충분히 쉬고 싶어요.'],array['슬픔','일상'])
    ) as items(number,email,feeling,concerns,emotions)
    loop
        select id into member_uuid from public.members where email=fixture.email;
        if not found then raise exception 'Apply local account seed first'; end if;
        suffix := lpad(fixture.number::text,12,'0');
        conversation_uuid := ('30000000-0000-4000-8000-' || suffix)::uuid;
        message_uuid := ('31000000-0000-4000-8000-' || suffix)::uuid;
        job_uuid := ('32000000-0000-4000-8000-' || suffix)::uuid;
        summary_uuid := ('34000000-0000-4000-8000-' || suffix)::uuid;
        if exists(select 1 from public.conversation_summaries where id=summary_uuid) then
            continue;
        end if;
        insert into public.conversations(id,member_id,phase,next_seq_no)
          values(conversation_uuid,member_uuid,'reviewing',2);
        insert into public.conversation_messages(id,conversation_id,seq_no,role,content,client_message_id)
          values(message_uuid,conversation_uuid,1,'user',fixture.feeling,message_uuid);
        -- Only a completed summary fixture for the existing FK; no image job or worker.
        insert into public.generation_jobs(id,member_id,conversation_id,kind,source_until_seq_no,
          idempotency_key,request_fingerprint,status,attempt_count,finished_at)
          values(job_uuid,member_uuid,conversation_uuid,'summary',1,job_uuid,
            'local-diary-summary-fixture','succeeded',1,clock_timestamp());
        insert into public.conversation_summaries(id,member_id,conversation_id,version,
          source_until_seq_no,current_feeling,main_concerns,emotion_tags,generation_job_id)
          values(summary_uuid,member_uuid,conversation_uuid,1,1,
            fixture.feeling,fixture.concerns,fixture.emotions,job_uuid);
    end loop;
end;
$$;
