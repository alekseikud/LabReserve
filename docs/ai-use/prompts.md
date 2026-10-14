# AI prompts

Short summaries of prompts used during the project. They are not a verbatim
chat export. Keep only the entries that match the AI assistance actually used.

## Git ignore

> What should I put in `.gitignore` for a Django, PostgreSQL, Docker and
> JavaScript project? Ignore environment files, Python cache, `node_modules`,
> test results and coverage files, but keep `.env.example`.

**Impact:** Helped define the final `.gitignore` rules.

## Docker ignore

> Make simple `.dockerignore` files for the Django backend and Nginx frontend.
> Do not exclude files needed to run the containers.

**Impact:** Helped keep unnecessary development files out of Docker images.

## Architecture

> Would it be fine to use two containers: one for PostgreSQL and one containing
> both the Django backend and frontend? Would it be better to separate the
> frontend, backend and database into three containers?

**Impact:** The discussion led to using three containers: PostgreSQL for the
database, Django for the backend and Nginx for the frontend. This separated
their responsibilities and let Nginx serve frontend files and proxy requests
to Django.

## Reservation tests

> What test cases should I add for equipment reservations? Include overlapping
> bookings, adjacent bookings, invalid dates, unavailable equipment,
> cancellation and two users booking at the same time.

**Impact:** Helped identify reservation and concurrency cases for backend tests.

## Login and permissions tests

> Suggest tests for students, laboratory managers and administrators. Check
> login, CSRF, access to other laboratories, inactive users and users trying to
> change records they do not own.

**Impact:** Helped extend the authentication and permission test coverage.

## Database tests

> Suggest a few PostgreSQL tests for unique equipment tags, reservation status,
> invalid time ranges, foreign keys and applying the SQL schema more than once.

**Impact:** Helped select database constraints and schema behaviour to test.

## Browser tests

> What Playwright tests should I use for login, booking equipment, approving a
> reservation and checking the pages on desktop and mobile?

**Impact:** Helped plan the main browser flows and responsive checks.

## JavaScript connection status

> Help me write the small JavaScript part for checking `/api/health`. It should
> show whether the backend is connected, display an error when it is down and
> let the user retry. Keep it simple and explain the code so I can adjust it.

**Impact:** Partially helped create the frontend connection-status JavaScript.

## JavaScript review

> Review my frontend JavaScript and simplify it where possible. Check that it
> handles failed requests and does not leave the retry button disabled.

**Impact:** Helped improve error handling and retry behaviour.

## Images and screenshots

> Which application screenshots should I include in the project report? I have
> login, equipment, reservation, manager and administrator pages. Suggest the
> most useful images and a sensible order.

**Impact:** Helped choose the screenshots and their order in the README.

## Screenshots

> Which Screenshots should I create according to the task description?

**Impact:** Led to including a mobile equipment-page screenshot + screenshots of pages in README.

## README

> Check my README and suggest what is missing. It should explain how to start
> the Docker containers, create accounts, use the booking system and run the
> tests. Keep the wording simple.

**Impact:** Helped organize the setup, usage and testing documentation.

## General formatting

There is no prompts since I used AI as primary formatter of Markdown or sometimes a code formatter(I mean best practices of code syntax, etc...).