select
  to_regclass('public.blueprint_sections') is not null as table_exists,
  (select relrowsecurity from pg_class where oid='public.blueprint_sections'::regclass) as rls_enabled,
  (select count(*) from pg_policies where schemaname='public' and tablename='blueprint_sections') = 4 as four_owner_policies,
  has_function_privilege('authenticated','public.get_blueprint_dashboard(uuid)','EXECUTE') as authenticated_can_read_dashboard,
  not has_function_privilege('anon','public.get_blueprint_dashboard(uuid)','EXECUTE') as anon_blocked;
