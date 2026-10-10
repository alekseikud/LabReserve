# LabReserve proposal

The idea is an application for booking university laboratory equipment.
It should help students find equipment and avoid booking the same item
at the same time.

There will be three roles:

- Student: browse equipment and manage their own reservations.
- Laboratory manager: manage equipment and approve reservations in their lab.
- Administrator: manage users and laboratories.

Users will log in and be able to reset their password. Equipment and reservation
lists will have filters. Students will choose equipment and a time, then wait
for a manager to approve the booking. Unavailable equipment and overlapping
bookings should be rejected.

The backend will use Django and PostgreSQL. The frontend will use HTML, CSS
and JavaScript. Database, backend and frontend will run in Docker containers.

First, set up the containers and database tables. Then add login, equipment
management and reservations. The pages should work on desktop and mobile,
and the project should include automated tests.
