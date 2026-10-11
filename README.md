# LabReserve

A university project for booking laboratory equipment.

Uses Django, PostgreSQL and a simple HTML/CSS/JavaScript frontend.
The project idea is in [docs/proposal.md](docs/proposal.md).

The containers, database tables and a basic frontend are set up.
Login and reservations are not implemented yet.

Django handles users and authentication. Laboratory, equipment and reservation
tables are defined in `backend/sql/001_initial.sql`. Startup runs Django migrations
first, then `python manage.py apply_sql_schema`. Applied SQL filenames are recorded
in `sql_schema_versions`; add a new numbered file for future schema changes.

## Run

Start Docker Desktop, then run:

```sh
cp .env.example .env
docker compose up -d --build --wait
```

Open http://localhost:8080. The page loads, but the connection check has a
known networking issue to fix next.

## Tests

```sh
npm ci --prefix frontend
cd frontend
npx playwright install chromium
npm test
```
