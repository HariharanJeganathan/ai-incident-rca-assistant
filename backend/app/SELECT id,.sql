SELECT id,
       incident_file,
       rca_report,
       impact_level,
       created_at
FROM public.incident_rca
LIMIT 1000;