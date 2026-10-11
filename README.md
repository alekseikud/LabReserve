# LabReserve

A university project for booking laboratory equipment.

Uses Django, PostgreSQL and a simple HTML/CSS/JavaScript frontend.
The project idea is in [docs/proposal.md](docs/proposal.md).

## Database setup

Start Docker Desktop, then run:

```sh
cp .env.example .env
docker compose up -d --wait database
sh scripts/check-database.sh
```

Database data is stored in a Docker volume.

## Backend

The backend has database tables and a health check. Login and reservations
are not implemented yet.

Django handles users and authentication. Laboratory, equipment and reservation
tables are defined in `backend/sql/001_initial.sql`. Startup runs Django migrations
first, then `python manage.py apply_sql_schema`. Applied SQL filenames are recorded
in `sql_schema_versions`; add a new numbered file for future schema changes.

```sh
docker compose up -d --build --wait backend
docker compose exec backend python manage.py test tests
```
