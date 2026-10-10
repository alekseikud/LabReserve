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
