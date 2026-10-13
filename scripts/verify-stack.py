#!/usr/bin/env python3
"""Verify a disposable Compose stack without modifying the development database."""

import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
PROJECT = f"labreserve-check-{uuid4().hex[:12]}"
ENV = {
    **os.environ,
    "FRONTEND_PORT": "0",  # Docker assigns an unused local port.
    "POSTGRES_DB": "labreserve_check",
    "POSTGRES_USER": "labreserve_check",
    "POSTGRES_PASSWORD": "disposable-test-password",
    "DJANGO_SECRET_KEY": "disposable-test-key-not-for-deployment",
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,backend",
    "EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend",
}
COMPOSE = [
    "docker", "compose", "--env-file", str(ROOT / ".env.example"),
    "--project-name", PROJECT, "--file", str(ROOT / "compose.yaml"),
]


def run(command, *, capture=False, env=None, timeout=600):
    result = subprocess.run(
        command, cwd=ROOT, env=env or ENV, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        timeout=timeout,
    )
    if result.returncode:
        if capture:
            print(result.stdout, end="")
            print(result.stderr, end="")
        raise subprocess.CalledProcessError(result.returncode, command)
    return result.stdout.strip() if capture else ""


def compose(*args, **kwargs):
    return run([*COMPOSE, *args], **kwargs)


def sql(statement):
    return compose(
        "exec", "-T", "database", "sh", "-ec",
        'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At -c "$1"',
        "psql", statement, capture=True,
    )


def base_url():
    address = compose("port", "frontend", "80", capture=True)
    return f"http://{address}"


def wait_health(base, expected_code, expected_body):
    deadline = time.monotonic() + 30
    last = None
    while time.monotonic() < deadline:
        try:
            try:
                with urlopen(f"{base}/api/health", timeout=6) as response:
                    code, body = response.status, response.read()
            except HTTPError as error:
                code, body = error.code, error.read()
            last = (code, body)
            if code == expected_code and json.loads(body) == expected_body:
                return
        except (URLError, TimeoutError, ValueError) as error:
            last = str(error)
        time.sleep(0.5)
    raise AssertionError(f"Health response did not become {expected_code}: {last}")


def verify():
    print(f"Starting isolated verification project: {PROJECT}", flush=True)
    compose("up", "-d", "--build", "--wait", "--wait-timeout", "120")
    base = base_url()
    wait_health(base, 200, {"status": "ok"})
    with urlopen(base, timeout=5) as response:
        assert b"LabReserve" in response.read(), "Frontend shell not served"
    print("PASS: fresh stack, Django auth migrations, SQL schema and proxied health", flush=True)

    for command in [
        ["check"],
        ["migrate", "--check"],
        ["apply_sql_schema", "--check"],
        ["apply_sql_schema"],  # A second application must leave data/schema intact.
        ["makemigrations", "--check", "--dry-run"],
        ["test", "tests", "--verbosity", "2"],
    ]:
        compose("exec", "-T", "backend", "python", "manage.py", *command)
    print("PASS: Django checks and PostgreSQL schema/health tests", flush=True)

    compose("stop", "database")
    wait_health(base, 503, {"status": "unavailable"})
    compose("up", "-d", "--no-deps", "--wait", "database")
    wait_health(base, 200, {"status": "ok"})
    print("PASS: real database outage returns 503; restart restores 200", flush=True)

    # Only this disposable stack receives the marker, never the development DB.
    marker = uuid4().hex
    sql("CREATE TABLE infrastructure_probe (value text PRIMARY KEY)")
    sql(f"INSERT INTO infrastructure_probe VALUES ('{marker}')")
    compose("down")  # Keep this test project's named volume for the next startup.
    compose("up", "-d", "--wait", "--wait-timeout", "120")
    assert sql("SELECT value FROM infrastructure_probe") == marker
    base = base_url()
    wait_health(base, 200, {"status": "ok"})
    print("PASS: data persists across removal and recreation of all containers", flush=True)

    # These accounts exist only in the disposable verification database.
    password = uuid4().hex
    compose("exec", "-T", "-e", f"AUTH_TEST_PASSWORD={password}", "backend", "python", "manage.py", "shell", "-c",
            "import os; from accounts.models import User; "
            "[User.objects.create_user('browser-' + role, role + '@example.test', "
            "os.environ['AUTH_TEST_PASSWORD'], role=role) for role in User.Role.values]")
    run(["npm", "test", "--prefix", "frontend"], env={**ENV, "BASE_URL": base, "AUTH_TEST_PASSWORD": password})
    print("PASS: browser authentication, permissions, reset forms and connection tests", flush=True)


if __name__ == "__main__":
    if not (ROOT / "frontend/node_modules/@playwright/test").is_dir():
        raise SystemExit("Run npm ci --prefix frontend and install Playwright Chromium first.")
    try:
        verify()
    finally:
        print(f"Removing disposable test resources for {PROJECT}", flush=True)
        # PROJECT is generated above, never accepted from user input. Only the
        # temporary project's containers/network/volume are removed; images stay.
        compose("down", "--volumes", "--remove-orphans", timeout=120)
