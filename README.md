# TAKT — MSP Operations Platform

A multi-tenant SaaS platform for Managed Service Providers, built with Python 3, Flask, and PostgreSQL.

## Features

- **Multi-tenancy** — PostgreSQL schema isolation per tenant
- **CRM** — Contact management with Markdown notes
- **Ticketing** — Full helpdesk with comments and time logging
- **Tasks** — Task management with start/stop timer and calendar view
- **Projects** — Project tracking linking tickets and tasks
- **Device Registration** — Asset inventory management
- **Billing** — Customer billing with subscriptions and invoices
- **Super Admin Portal** — Tenant management, MSP billing, impersonation

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- pip

---

## Setup

### PowerShell (Windows)

#### 1. Create and activate a virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

> If you get an execution policy error, run first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

#### 3. Create the PostgreSQL database

```powershell
createdb takt
```

Or via psql:
```sql
CREATE DATABASE takt;
```

#### 4. Set environment variables

```powershell
$env:DATABASE_URL = "postgresql://localhost/takt"
$env:SECRET_KEY   = "your-secret-key-here"
```

These are session-scoped. To make them permanent across terminals, use a `.env` file instead (see below) — it is loaded automatically by the app.

Or create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://localhost/takt
SECRET_KEY=your-secret-key-here
```

If your PostgreSQL user requires a password:
```env
DATABASE_URL=postgresql://username:password@localhost/takt
```

#### 5. Run the seed script

```powershell
python seed.py
```

#### 6. Run the application

```powershell
python run.py
```

The app starts at **http://127.0.0.1:5000**

---

### bash / macOS / Linux

#### 1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

#### 3. Create the PostgreSQL database

```bash
createdb takt
```

Or using psql:
```sql
CREATE DATABASE takt;
```

#### 4. Set environment variables

```bash
export DATABASE_URL="postgresql://localhost/takt"
export SECRET_KEY="your-secret-key-here"
```

Or create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://localhost/takt
SECRET_KEY=your-secret-key-here
```

If your PostgreSQL user requires a password:
```env
DATABASE_URL=postgresql://username:password@localhost/takt
```

#### 5. Run the seed script

```bash
python seed.py
```

#### 6. Run the application

```bash
python run.py
```

The app starts at **http://127.0.0.1:5000**

---

## Login URLs & Credentials

### Super Admin Portal
- **URL**: http://127.0.0.1:5000/admin/login
- **Username**: `admin`
- **Password**: `admin123`

### Demo Tenant
- **URL**: http://127.0.0.1:5000/t/demo/login
- **Admin**: `demo_admin` / `demo123`
- **User 1**: `alice` / `demo123`
- **User 2**: `bob` / `demo123`

---

## Project Structure

```
takt/
  app/
    __init__.py          # App factory, blueprint registration
    extensions.py        # db, login_manager, csrf
    models/
      public.py          # Tenant, SuperAdminUser, billing models
      tenant.py          # User, Site, CRM, Ticketing, Tasks, etc.
    middleware/
      tenant.py          # URL-based tenant resolution, schema switching
      module_guard.py    # @module_required, @admin_required decorators
    blueprints/
      auth/              # Login/logout, user & site management
      super_admin/       # Tenant CRUD, MSP billing, impersonation
      dashboard/         # Per-tenant dashboard
      crm/               # Contact management
      ticketing/         # Helpdesk tickets
      tasks/             # Task management + calendar
      projects/          # Project management
      devices/           # Device registry
      billing/           # Customer billing
    templates/           # Jinja2 templates (Bootstrap 5)
    static/
      style.css
config.py
run.py
seed.py
requirements.txt
```

---

## Adding a New Tenant

1. Log in as super admin at `/admin/login`
2. Navigate to **Tenants → New Tenant**
3. Set a name and slug (e.g. `acme`)
4. Select enabled modules
5. Click **Save** — the schema is provisioned automatically
6. Tenant users can log in at `/t/acme/login`

---

## Architecture Notes

- **Multi-tenancy**: Each tenant gets a dedicated PostgreSQL schema (`tenant_{slug}`). The middleware sets `SET search_path TO tenant_{slug}, public` on every request, so all ORM queries transparently resolve to the correct schema.
- **Module flags**: Each module (CRM, Ticketing, etc.) is gated by `TenantModule` records. The `@module_required('crm')` decorator enforces this at route level; the sidebar only shows enabled modules.
- **Auth**: Flask-Login with dual user types — `SuperAdminUser` (public schema) and tenant `User` (tenant schema). User IDs are prefixed (`admin:1` vs `tenant:demo:1`) for the user_loader to distinguish them.
- **No Celery**: The task timer uses Flask session storage. Start time is stored in session; on stop, a `TaskTimeEntry` record is created.