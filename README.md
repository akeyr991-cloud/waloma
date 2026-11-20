# WALOMA — Association Management System

WALOMA is a responsive association-management application designed for phones, tablets, and desktop computers. This repository is delivered in three coordinated packages. **Part 1** establishes the shared project foundation and implements the database, authentication, roles, and member registration workflow.

All application interface text and project documentation are in English.

## Part 1 scope

Implemented in this package:
- FastAPI application with versioned `/api/v1` endpoints.
- PostgreSQL configuration and SQLAlchemy 2 models.
- Alembic initial database migration.
- Password hashing using Argon2 and signed bearer access tokens.
- Four roles: `admin`, `treasurer`, `secretary`, and `member`.
- Member registration with generated `WAL-YYYY-000001`-style IDs.
- Pending approval workflow; pending accounts cannot sign in.
- Admin-only pending-registration list and approve/reject endpoint.
- Responsive English login/registration starter page using the supplied WALOMA logo.
- Docker Compose development setup and automated tests.

Not yet included (reserved for Parts 2 and 3): full member administration, meetings, attendance, financial transactions, receipts, announcements, push/SMS notifications, exports, offline/PWA synchronization, production Nginx/HTTPS, and backup automation.

## Architecture

- `app/api`: HTTP endpoints and authorization dependencies.
- `app/core`: configuration and security primitives.
- `app/db`: SQLAlchemy base and database session.
- `app/models`: persistent domain models.
- `app/schemas`: API request/response validation.
- `app/services`: reusable domain services.
- `frontend`: responsive starter interface and WALOMA brand asset.
- `alembic`: versioned database migrations.
- `tests`: automated API tests.

The package layout and API versioning are intended to remain stable as Parts 2 and 3 add modules.

## Run with Docker Compose

1. Install Docker Engine and the Docker Compose plugin.
2. Copy `.env.example` to `.env`.
3. Set a long, unique `SECRET_KEY`, a strong `BOOTSTRAP_ADMIN_PASSWORD`, and a strong `POSTGRES_PASSWORD`. Keep `.env` private.
4. Ensure `DATABASE_URL` uses the same PostgreSQL password as `POSTGRES_PASSWORD` (Compose sets the database URL from `POSTGRES_PASSWORD`).
5. Start the stack:

   ```bash
   docker compose up --build -d
   ```

6. Create the initial administrator:

   ```bash
   docker compose exec app python -m scripts.create_admin
   ```

7. Open `http://localhost:8000`. API documentation is at `http://localhost:8000/docs`; health check is at `http://localhost:8000/health`.

The initial administrator is created by an explicit command, not silently on every application startup. Change the bootstrap password after setup and remove it from the environment when no longer needed.

## Run locally without Docker

Use Python 3.12 or later and a PostgreSQL database. Create and activate a virtual environment, install dependencies, copy `.env.example` to `.env`, and set a reachable `DATABASE_URL`.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.create_admin
uvicorn app.main:app --reload
```

For a quick local-only smoke test, the default configuration can use SQLite; PostgreSQL is the intended shared deployment database.

## Authentication and registration API

- `POST /api/v1/auth/register` — public registration; creates a pending member.
- `POST /api/v1/auth/login` — returns a bearer token only for approved, active accounts.
- `GET /api/v1/auth/me` — returns the authenticated user's safe profile.
- `GET /api/v1/auth/registrations/pending` — admin-only pending registrations.
- `PATCH /api/v1/auth/registrations/{user_id}/status` — admin-only approval or rejection. JSON body: `{"status":"approved"}` or `{"status":"rejected"}`.

Registration JSON example:

```json
{
  "full_name": "Example Member",
  "email": "member@example.com",
  "phone": "+251911000000",
  "password": "Use-A-Strong-Password"
}
```

Passwords must contain at least 10 characters. Never send passwords in URLs or log them. Tokens should be sent in the `Authorization: Bearer <token>` header.

## Run automated tests

```bash
pytest -q
```

## Security and deployment notes

This is the first development package, not a claim of production certification. Before public deployment, configure HTTPS, secure secrets, restrict CORS to the real frontend origin, use a strong database password, enforce operational monitoring, and review the deployment against the association's security requirements. Production reverse proxy, TLS automation, backup/restore procedures, and offline conflict handling are scheduled for Part 3.

## Part 2 modules

Part 2 extends this same project with the following API groups under `/api/v1`:

- `GET /members`, `PATCH /members/{member_id}` — staff member directory and administrator profile/account updates.
- `POST /meetings`, `GET /meetings` — create and list association meetings.
- `POST /meetings/{meeting_id}/attendance`, `GET /meetings/{meeting_id}/attendance` — attendance recording and review.
- `POST /contributions`, `GET /contributions` — monthly contribution obligations and calculated paid/balance totals.
- `POST /payments`, `GET /payments` — partial or final payments using cash, bank, or mobile methods.
- `GET /receipts/{receipt_number}.pdf` — authenticated PDF receipt download.

Apply the Part 2 schema update with `alembic upgrade head`. The Part 2 package contains the full project, including all Part 1 files, and should be extracted over the same `WALOMA/` project folder.

### Part 2 authorization notes

- Administrators and secretaries can create meetings and mark attendance.
- Administrators and treasurers can create contribution obligations and record payments.
- Administrators, treasurers, and secretaries can view the member directory.
- Administrators can update member names, phone numbers, and active status.
- Members can view their own contribution balances and payment history and download their own receipts.
- Contribution creation accepts the public WALOMA Member ID shown in the member directory.

### Part 2 validation

Automated tests cover authentication from Part 1, member-directory authorization, meeting attendance and duplicate prevention, partial payment/balance handling, overpayment rejection, PDF receipt generation, and public Member ID lookup. See `tests/`.
