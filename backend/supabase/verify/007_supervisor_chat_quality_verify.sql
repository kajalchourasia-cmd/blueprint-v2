-- Run after migration 007. A healthy result is one row of all true values.
select
  (
    select count(*) = 4
    from pg_class
    where oid in (
      to_regclass('public.run_contexts'),
      to_regclass('public.chat_threads'),
      to_regclass('public.chat_messages'),
      to_regclass('public.agent_commands')
    )
  ) as all_phase6_tables_exist,
  (
    select count(*) = 4 and bool_and(relrowsecurity)
    from pg_class
    where oid in (
      to_regclass('public.run_contexts'),
      to_regclass('public.chat_threads'),
      to_regclass('public.chat_messages'),
      to_regclass('public.agent_commands')
    )
  ) as all_phase6_tables_have_rls,
  (
    select count(*) = 11
    from pg_policies
    where schemaname = 'public'
      and tablename in ('run_contexts', 'chat_threads', 'chat_messages', 'agent_commands')
  ) as all_owner_policies_exist,
  has_function_privilege('authenticated', 'public.get_supervisor_context(uuid)', 'execute')
    as authenticated_can_read_supervisor_context,
  not has_function_privilege('anon', 'public.get_supervisor_context(uuid)', 'execute')
    as anon_is_blocked_from_supervisor_context;
