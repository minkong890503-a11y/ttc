# TTC

TTC is a workspace for hospital/clinic operations tools.

## Structure

```text
apps/
  beauty_app/        Flask + SQLite CRM and closing app
automations/         Automation tools will be added later after cleanup
```

## Current Status

The first cleaned project added here is `apps/beauty_app`.

Excluded from Git:

- local databases (`*.db`, `*.sqlite`)
- virtual environments (`venv/`, `.venv/`)
- secrets (`.env`, tokens, sessions, cookies)
- browser profiles and caches
- runtime outputs/logs/data

## Beauty App

```powershell
cd apps\beauty_app
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:BEAUTY_APP_SECRET_KEY='change-this-local-secret'
$env:BEAUTY_APP_ADMIN_PASSWORD='change-this-admin-password'
.\.venv\Scripts\python.exe app.py
```

The app initializes a local SQLite database when it runs. Do not commit local database files.
