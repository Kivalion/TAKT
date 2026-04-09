# Coding Baseline — Vincent
This file defines how to approach all coding tasks. Apply it to every project,
every language, from the first line of code to delivery.
---
## Core Principles
Security is non-negotiable — apply the highest available security standard by
default, in every language, every project type, every time. Never downgrade for
convenience.
Code is self-documenting — use clear naming over comments. Add comments only
when the why is non-obvious (not the what).
Explain after, not during — write the code first, then give a structured
step-by-step explanation below it.
Write files by default — Claude Code has full filesystem access; always write
code to disk rather than printing long blocks inline.
Minimal surface area — don't add features that weren't asked for.
Fail loudly — prefer explicit errors over silent failures. Never swallow
exceptions without logging or re-raising.
---
## Output Format
| Situation | Action |
|---|---|
| Snippet / single function / < ~20 lines | Inline in chat |
| Any complete script, module, or multi-file project | Write to disk |
| Config files, `.env.example`, `.gitignore`, `README.md` | Always write to disk |
| PowerShell scripts | Always write as `.ps1` file |

After writing files, always give a step-by-step explanation of what was built,
structured as numbered steps matching the code flow.
---
## Security Baseline (ALL languages, ALL projects)
Security is built in from the start — never bolted on later.

### Transport & Communication
Always use HTTPS — never HTTP for any external communication.
Never disable certificate verification (`verify=False`, `--insecure`,
`rejectUnauthorized: false` are forbidden in production code).
WebSockets: use `wss://` only.
Set timeouts on all outbound requests — never leave connections open-ended.

Flask web apps — HTTPS mandatory in all environments

Development — `pyopenssl` for self-signed cert (browser shows warning, acceptable):
```bash
pip install pyopenssl   # add to requirements.txt
```
```python
app.run(debug=False, host="127.0.0.1", port=5000, ssl_context="adhoc")
```
Production — Let's Encrypt via certbot + nginx reverse proxy:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.nl
sudo systemctl enable certbot.timer
```
Nginx config (production):
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.nl;
    ssl_certificate     /etc/letsencrypt/live/yourdomain.nl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.nl/privkey.pem;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
server {
    listen 80;
    server_name yourdomain.nl;
    return 301 https://$host$request_uri;
}
```
Add to Flask app when using nginx:
```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
```
> Windows/internal network without public domain: use internal CA or keep using `adhoc`.

### Secrets & Credentials
Never hardcode secrets — no passwords, API keys, tokens, or connection strings.
Load secrets from environment variables or a secrets manager (`.env` +
`python-dotenv`, Azure Key Vault, Windows Credential Manager, Secret Server).
Always add `.env` to `.gitignore`; always provide `.env.example` with placeholders.
Secrets stored at rest must be encrypted — never plaintext.

### Token & Session Security
Use short-lived tokens with explicit expiry.
Store tokens in memory or `HttpOnly` cookies — never in `localStorage`.
Hash passwords with `bcrypt` or `argon2` — never MD5, SHA1, or plain SHA256.

### Input Validation & Injection Prevention
Validate and sanitize all user input before use.
Parameterized queries / ORM only — never string-concatenate SQL.
Escape output in HTML contexts to prevent XSS.
Reject unexpected input with a clear error.

### Permissions & Least Privilege
Scripts and services run with the minimum permissions required.
API integrations: request only the scopes needed.
File operations: explicit paths only, never `chmod 777`.

### Logging & Error Handling
Never log secrets, tokens, passwords, or credential-containing request bodies.
Return generic error messages to end users; log detail server-side.
PowerShell: use `ConvertTo-SecureString` / `PSCredential` for passwords.

### Dependencies
Pin versions in `requirements.txt`, `package.json`, etc.
Flag known vulnerabilities when encountered.

### Security Notes in Explanation
After any code that handles credentials, tokens, network calls, or user input,
always add:
```
**Security notes:**
- [What is secured and how]
- [What still needs to be arranged, e.g. put secrets in .env]
```
---
## Language Conventions

### Python
Type hints on all function signatures.
`pathlib.Path` over `os.path`.
f-strings only — not `.format()` or `%`.
Structure: imports → constants → functions/classes → `if __name__ == "__main__"`.
Specific exception types; log before raising or re-raising.

### PowerShell
`#Requires -Version 5.1` where relevant.
`[CmdletBinding()]` and `param()` on all scripts with parameters.
`try/catch/finally` over `$?` checks for critical operations.
`Write-Verbose` for debug output, not `Write-Host`.
Output objects, not strings — enables pipeline compatibility.
Variables: `$PascalCase`. Functions: `Approved-Verb` (Get-, Set-, New-, Remove-...).

### Bash / Shell
Always: `#!/usr/bin/env bash` + `set -euo pipefail`.
Quote all variables: `"$VAR"`.
`[[ ]]` over `[ ]` for conditionals.
Usage/help text for any script with parameters.

### JavaScript / TypeScript
`const` by default, `let` only when reassignment is needed.
`async/await` always — never raw `.then()` chains.
TypeScript: interfaces for object shapes, `type` for unions.

### React
Functional components only.
One component per file.
Tailwind for styling unless the project uses something else.

### SQL
Keywords uppercase (`SELECT`, `WHERE`, `JOIN`).
Always alias tables in multi-table queries.
Add indexes on columns used in WHERE/JOIN in schema definitions.
Note the target DB (PostgreSQL, SQLite, MSSQL) — syntax varies.

---
## Project Setup
When starting a new project, before writing any code:
Show the intended folder structure.
List dependencies and how to install them.
Identify the entry point and startup command.
Note required `.env` variables.
Only proceed after confirmation.

Always create at project start:
`.gitignore` (language-appropriate + `.env`, `*.key`, `*.pem`, `secrets.*`)
`.env.example` with placeholder values
`README.md` with: purpose, requirements, install, usage

---
## Idempotency
Scripts that create, configure, or delete resources must be safely runnable
multiple times.
Check-before-act: verify whether a resource already exists before creating/modifying.
Clearly report when something is already in the desired state.
Never assume that a previous run succeeded — re-validate.
Destructive actions: offer `-WhatIf` / `--dry-run`.

---
## Structured Logging
| Level | When |
|---|---|
| DEBUG | Internal state, dev only |
| INFO | Normal operational events |
| WARNING | Unexpected but recoverable |
| ERROR | Action failed |
| CRITICAL | System cannot continue |

Python: use `logging.basicConfig` with timestamp + level in the format
`%(asctime)s [%(levelname)s] %(message)s`.
PowerShell: write to logfile and console via `Tee-Object`.
Never log: passwords, tokens, secrets, response bodies with credentials.

---
## Environment Separation
`.env` or environment variables — never hardcoded environment values.
Give a clear error message for missing required variables at startup.
Never use production endpoints as default — use dev/test as fallback.

---
## Audit Trail (admin scripts)
Scripts that touch AD, Intune, M365, firewalls, or servers always log:
Timestamp · User · Hostname · Action · Target resource · Result
```powershell
function Write-Audit {
    param([string]$Action, [string]$Target, [string]$Result, [string]$Detail = "")
    [PSCustomObject]@{
        Timestamp = (Get-Date -Format "o")
        User      = "$env:USERDOMAIN\$env:USERNAME"
        Host      = $env:COMPUTERNAME
        Action    = $Action
        Target    = $Target
        Result    = $Result
        Detail    = $Detail
    } | Export-Csv -Path $AuditLog -Append -NoTypeInformation -Encoding UTF8
}
```
Store audit logs outside the script directory — network share or SIEM.

---
## Retry & Resilience
All external calls have: max 3 retries, exponential backoff (1s → 2s → 4s),
and an explicit timeout. Non-idempotent actions (POST, delete) only retry
after confirming the action did not already succeed.
Python: use `tenacity` (`@retry` decorator).
PowerShell: use an `Invoke-WithRetry` helper with `do/try/catch`.

---
## Code Review Mode
Categorize issues: correctness, security, performance, maintainability.
Show critical issues first.
Always show the improved version — not just the criticism.
Preserve the original intent — don't refactor beyond what was asked.

---
## Debugging Mode
Establish: expected vs. actual behavior.
Isolate: smallest reproducible case.
Form a hypothesis about the cause before changing anything.
After the fix, explain why it was wrong, not just what changed.

---
## Explanation Format
After every code description:
```
**How it works:**
1. [First step]
2. [Next step]
...
**Note:** [edge cases, requirements, limitations]
```
For code < 10 lines: one concise paragraph is sufficient.

---
## Never Do
- Hardcode secrets, tokens, passwords, or keys — ever.
- Disable TLS/SSL verification.
- Use HTTP instead of HTTPS.
- Store passwords in plaintext.
- Use MD5 or SHA1 for anything security-sensitive.
- Concatenate user input into SQL, shell commands, or HTML.
- Suggest `chmod 777` or world-readable permissions.
- Log sensitive data (tokens, credentials, PII).
- Add unrequested features or boilerplate.
- Use `print()` for debug output in delivered code.
- Add structural comments like `# End of function`.

---
## Authentication (required for every web application)
Every web application has authentication — no exceptions.
Use `flask-login` for session management.
Always hash passwords with `bcrypt` — never plaintext, MD5, or SHA1.
Default credentials via `.env`: `ADMIN_USER` and `ADMIN_PASSWORD_HASH`.
Generate hash at setup: `python -c "import bcrypt; print(bcrypt.hashpw(b'admin', bcrypt.gensalt()).decode())"`
Rate-limit login endpoints: max 5 attempts per minute.
`LOGIN_REQUIRED=true` in `.env` — can be disabled for dev, always on in production.
`/health` and `/static` are always exempt from auth.

---
## Health Check Endpoints
Every web application has a `/health` endpoint:
```python
@app.route("/health")
def health():
    checks = {"status": "ok", "database": "ok"}
    try:
        with database.get_connection(DATABASE_PATH) as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        checks["database"] = str(e)
        checks["status"] = "degraded"
    return jsonify(checks), 200 if checks["status"] == "ok" else 503
```
Zabbix HTTP item: `https://host/health` → JSON path `$.status` → trigger if != `ok`.

---
## Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "60 per hour"])

@app.route("/api/devices", methods=["POST"])
@limiter.limit("10 per minute")
def create_device(): ...

# Login always strict
@app.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login(): ...
```

---
## Docker
Base image: `python:3.12-slim`
Non-root user (`appuser`) required
Secrets via environment — never baked into image
`HEALTHCHECK` based on `/health` endpoint
`.dockerignore`: `.env`, `*.db`, `.git`, `__pycache__`
`docker-compose.yml` for dev, `docker-compose.prod.yml` with nginx for production

---
## Systemd Service
Dedicated non-root user per service
`Restart=on-failure`, `RestartSec=5`
`EnvironmentFile=` pointing to `.env`
`StandardOutput=journal` — logs via journalctl
Hardening: `NoNewPrivileges=true`, `ProtectSystem=strict`, `PrivateTmp=true`

---
## Database Migrations (Alembic)
Initialize at project start: `alembic init migrations`
Every schema change = new revision, never manual SQL on production
At deployment always run first: `alembic upgrade head`
Always commit migrations in git

---
## Testing Baseline (pytest)
`tests/conftest.py` with app/client/db fixtures (in-memory SQLite for tests)
Per module minimum: happy path + error path
`pytest tests/ -v` before every commit
Flask: use `pytest-flask` and `app.test_client()`
