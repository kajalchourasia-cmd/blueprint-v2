-- Healthy result: one row of all true values.
select
  (
    select data_type = 'ARRAY' and udt_name = '_text'
    from information_schema.columns
    where table_schema = 'public' and table_name = 'chat_messages' and column_name = 'citation_ids'
  ) as chat_citation_ids_are_text_array,
  has_function_privilege('authenticated', 'public.persist_supervisor_result(jsonb)', 'execute')
    as authenticated_can_persist_supervisor,
  not has_function_privilege('anon', 'public.persist_supervisor_result(jsonb)', 'execute')
    as anon_cannot_persist_supervisor,
  has_function_privilege('authenticated', 'public.append_chat_exchange(jsonb)', 'execute')
    as authenticated_can_append_chat,
  not has_function_privilege('anon', 'public.append_chat_exchange(jsonb)', 'execute')
    as anon_cannot_append_chat;
