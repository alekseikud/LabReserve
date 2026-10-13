# LabReserve

A university project for booking laboratory equipment.

Uses Django, PostgreSQL and a simple HTML/CSS/JavaScript frontend.
The project idea is in [docs/proposal.md](docs/proposal.md).

The database, frontend, health check, login/logout, password reset and role access work.
Equipment browsing and reservations are not implemented yet.

Django handles users and authentication. Laboratory, equipment and reservation
tables are defined in `backend/sql/001_initial.sql`. Startup runs Django migrations
first, then `python manage.py apply_sql_schema`. Applied SQL filenames are recorded
in `sql_schema_versions`; add a new numbered file for future schema changes.

## Run

Start Docker Desktop, then run from the project folder:

```sh
# Only copy this on first setup.
cp .env.example .env
docker compose up -d --build --wait
```

Open http://localhost:8080. Stop with `docker compose down`.
Database data is kept unless you add `-v`.

Password reset is available from the login page. In local development, emails
are printed by `docker compose logs backend`, not delivered to an inbox.
The reset link expires after one hour. For real email delivery, configure the
SMTP settings shown in `.env.example` and recreate the backend container.
Do not share backend logs containing reset links.

## Accounts

Create accounts from the terminal (the password is prompted, not stored in a command):

```sh
docker compose exec backend python manage.py create_account student student@example.test
docker compose exec backend python manage.py create_account manager manager@example.test --role manager
docker compose exec backend python manage.py create_account administrator admin@example.test --role admin
```

Open http://localhost:8080/accounts/login/. Students can access their account page;
managers also get the manager area; administrators get both management areas.
The management areas are placeholders with real permission checks, not CRUD pages yet.
There is no public registration. Use a real email address when testing SMTP delivery.
The current local setup uses HTTP; configure HTTPS and secure cookies before public deployment.

## Tests

Backend: `docker compose exec backend python manage.py test tests`.

For browser tests, install Node.js 22 and run:

```sh
npm ci --prefix frontend
cd frontend
npx playwright install chromium
npm test
```

From the project folder, `python3 scripts/verify-stack.py` runs all checks
in a separate temporary Docker setup.
