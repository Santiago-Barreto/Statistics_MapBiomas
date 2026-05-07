# Supabase setup for v2.0.0

## 1) Run database schema
In your Supabase project SQL editor, run the script:

- `data/supabase_schema.sql`

This creates tables, indexes, RLS policies and RPC functions:
- `acquire_sync_lock`
- `release_sync_lock`

## 2) Configure Streamlit secrets
In Streamlit Cloud app settings, add:

```
SUPABASE_URL = "https://rolxlgwlgzudjakwviez.supabase.co"
SUPABASE_ANON_KEY = "<your-anon-key>"
```

## 3) Deploy app version v2.0.0
- If Streamlit Cloud is connected to `main`, deployment starts automatically after push.
- If you deploy by tag/commit, select tag `v2.0.0`.

## 4) Validate production behavior
- Open two browser sessions and load the app.
- Confirm that only one sync runs per 10-minute window.
- Confirm dashboards load without local SQLite errors.
