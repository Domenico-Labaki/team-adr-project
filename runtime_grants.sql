\set ON_ERROR_STOP on

BEGIN;

REVOKE CREATE ON SCHEMA public FROM PUBLIC, :"runtime_role";
GRANT USAGE ON SCHEMA public TO :"runtime_role";

GRANT SELECT, INSERT, UPDATE ON public."user", public.destination TO :"runtime_role";
GRANT SELECT, INSERT, DELETE ON public.favorite TO :"runtime_role";
GRANT SELECT, INSERT, UPDATE, DELETE ON public.itinerary, public.itinerary_stop TO :"runtime_role";

REVOKE ALL ON public.audit_log FROM PUBLIC, :"runtime_role";
GRANT INSERT ON public.audit_log TO :"runtime_role";
GRANT USAGE ON SEQUENCE public.user_id_seq, public.favorite_id_seq, public.destination_id_seq,
    public.itinerary_id_seq, public.itinerary_stop_id_seq, public.audit_log_id_seq TO :"runtime_role";

COMMIT;
